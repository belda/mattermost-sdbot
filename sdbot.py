'''
SD bot for Mattermost is connecting to Mattermost server on 1 side and to stable diffusion UI on the other side.

The but runs a main loop, where it awaits the SD UI server to be ready and then it connects to Mattermost server.
If the connection to SD server is lost, the connection to Mattermost is closed as well and the bot waits for
the SD server to be ready again to reconnect to both servers.
'''
import base64
import json
import random
import time
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4
from slugify import slugify
import os
from mattermostdriver import Driver
import requests


BOT_TOKEN = os.environ.get('MMBOT_TOKEN','')
MM_SERVER_URL = os.environ.get('MM_SERVER_URL','')
SD_SERVER_URL = os.environ.get('SD_SERVER_URL','')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE',4))


def ping() -> bool:
    ''' Checks if the SD server is ready to accept requests '''
    try:
        response = requests.get(SD_SERVER_URL+'/ping', timeout=5)
        assert response.status_code == 200
        assert response.json()['status'] in ('Online', 'Rendering')
        return True
    except:
        return False


def render_image(prompt : str) -> str:
    ''' Requests rendering of an image from the server and gives back the id location where the result is gonna be '''
    rq_data = {
        'prompt': prompt,
        'negative_prompt': 'letters',
        'seed': random.randint(0, 2**32-1),
        'width': 512,
        'height': 512,
        'num_outputs': 1,
        'num_inference_steps': 60,
        'guidance_scale': 7.5,
        'prompt_strength': 0.8,
        'sampler_name': 'euler_a',
        'hypernetwork_strength': 0,
        'lora_alpha': 0,
        'preserve_init_image_color_profile': False,
        'use_face_correction': 'GFPGANv1.3.pth',
        'use_upscale': 'RealESRGAN_x4plus.pth',
        'upscale_amount': 4,
        'vrma_usage_level': 'balanced',
        'use_stable_diffusion_model': 'sd-v1-4.ckpt',
        'use_vae_model': None,
        'use_hypernetwork_model': None,
        'use_lora_model': None,
        'show_only_filtered_image': True,
        'block_nsfw': False,
        'output_format': 'jpeg',
        'output_quality': 75,
        'output_lossless': False,
        'metadata_output_format': 'none',
        'stream_image_progress': False,
        'stream_image_progress_interval': 5
    }
    response = requests.post(SD_SERVER_URL+'/render', json=rq_data)
    assert response.status_code == 200
    return response.json()['task']


def load_concatenated_json(json_string):
    decoder = json.JSONDecoder()
    json_objects = []
    idx = 0

    while idx < len(json_string):
        try:
            obj, idx = decoder.raw_decode(json_string, idx)
            json_objects.append(obj)
        except:
            break

    return json_objects


def fetch_image(task_id : str) -> Optional[str]:
    ''' Fetches the image from the server and returns it as a base64 string '''
    response = requests.get(f'{SD_SERVER_URL}/image/stream/{task_id}')
    assert response.status_code == 200
    # response may return multiple json objects, we need to find the one with the image
    rsp_data = load_concatenated_json(response.text)
    for rsp in rsp_data:
        if 'status' in rsp and rsp['status'] == 'succeeded':
            header, image_base64 = rsp['output'][0]['data'].split(",", 1)
            return image_base64
    return None


def get_driver(server_url, token) -> Driver:
    ''' Parses the url and constructs dict for connection to the driver, it then returns the Driver instance '''
    url = urlparse(server_url)
    return Driver({
        'url': url.netloc,
        'port': url.port if url.port else 443,
        'basepath': '/api/v4',
        'token': token,
        'scheme': url.scheme,
        'verify': True
    })


def upload_mm_image(driver : Driver, channel_id: str, image_data: str, filename: Optional[str]) -> str:
    if not filename:
        filename = f'{uuid4()}.jpeg'
    # save base64 image to file
    with open("/tmp/"+filename, 'wb') as f:
        f.write(base64.b64decode(image_data))
    # upload the file to mattermost
    file_id = driver.files.upload_file(
        channel_id=channel_id,
        files={'files': (filename, open("/tmp/"+filename, 'rb'))}
    )['file_infos'][0]['id']
    # delete the file
    os.remove("/tmp/"+filename)
    return file_id


def extract_prompt(message: str, username: str) -> str:
    ''' Extracts the prompt from the message, it stripse everything before the @username and everything after the first newline following the prompt '''
    initial_index = message.index(f'@{username}') + len(f'@{username}') + 1
    message = message[initial_index:].strip()
    return message[: message.index('\n')] if '\n' in message else message


def main() -> None:
    driver = get_driver(MM_SERVER_URL, BOT_TOKEN)

    while not ping():
        print('Waiting for server to come online...')
        time.sleep(5)

    driver.login()
    my_user = driver.users.get_user('me')
    print(f"Logged in! My user is id={my_user['id']}, username={my_user['username']}")

    async def handle_event(input):
        data = json.loads(input)
        if data.get('event') == 'posted':
            post = json.loads(data.get('data').get('post'))
            message = post.get('message')
            channel_id = post.get('channel_id')

            if post.get('user_id') == my_user['id']:
                return
            if f'@{my_user["username"]}' not in message:
                return

            prompt = extract_prompt(message, my_user['username'])

            # now render the image and send it back
            image_ids = []
            for i in range(1, BATCH_SIZE+1):
                print(f'Rendering image {i} for prompt: {prompt}')
                task_id = render_image(prompt)

                image = None
                while image is None:
                    # TODO notify that we are waiting (typing)
                    print(f'Waiting for image {i} to be rendered...')
                    time.sleep(.7)
                    image = fetch_image(task_id)

                print(f'Image {i} rendered, uploading to Mattermost...')
                filename = slugify(prompt) + f'_{i}.jpeg'
                image_ids.append( upload_mm_image(driver, channel_id, image, filename) )

                driver.posts.create_post(options={
                    'channel_id': channel_id,
                    # 'message': f'*{prompt}*',
                    'root_id': post['root_id'] if post['root_id'] != '' else post['id'],
                    'file_ids': image_ids
                })

    driver.init_websocket(handle_event)


if __name__ == '__main__':
    main()