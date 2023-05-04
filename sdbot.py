'''
SD bot for Mattermost is connecting to Mattermost server on 1 side and to stable diffusion UI on the other side.

The but runs a main loop, where it awaits the SD UI server to be ready and then it connects to Mattermost server.
If the connection to SD server is lost, the connection to Mattermost is closed as well and the bot waits for
the SD server to be ready again to reconnect to both servers.
'''
import base64
import json
import random
import threading
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from mattermostdriver.exceptions import InvalidOrMissingParameters
from slugify import slugify
import os
from mattermostdriver import Driver
import requests
import pickle


BOT_TOKEN = os.environ.get('MMBOT_TOKEN','')
MM_SERVER_URL = os.environ.get('MM_SERVER_URL','')
SD_SERVER_URL = os.environ.get('SD_SERVER_URL','')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE',4))
NO_RESPONSE_USERNAMES = os.environ.get('NO_RESPONSE_USERNAMES','').split(',')
ONCE_ONLY_RESPONSE_USERNAMES = os.environ.get('ONCE_ONLY_RESPONSE_USERNAMES','chatgpt').replace('@','').split(',')
DATA_FILE = os.environ.get('DATA_FILE','data.pickle')


class Data:
    last_check_ts = 0
    responded_to_threads = set()
    responded_to_messages = set()

    def __init__(self):
        ''' Load data from DATA_FILE '''
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE,'rb') as f:
                data = pickle.load(f)
                self.last_check_ts = data.last_check_ts
                self.responded_to_threads = data.responded_to_threads
                self.responded_to_messages = data.responded_to_messages

    def save(self):
        ''' Save data to DATA_FILE '''
        with open(DATA_FILE,'wb') as f:
            pickle.dump(self,f)

    def add_thread(self,channel_id):
        self.responded_to_threads.add(channel_id)
        self.save()

    def add_message(self,message_id):
        self.responded_to_messages.add(message_id)
        self.save()

    def check(self, ts = datetime.now().timestamp()):
        ''' Ticke the last check timestamp '''
        self.last_check_ts = int(ts)
        self.save()




db = Data()


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


def process_post(driver: Driver, my_user:dict, post: dict) -> None:
    ''' Processes the post and replies to it with the image '''
    message = post.get('message')
    channel_id = post.get('channel_id')

    if shall_i_respond(my_user, post):
        prompt = extract_prompt(message, my_user['username'])

        # now render the image and send it back
        image_ids = []
        for i in range(1, BATCH_SIZE + 1):
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
            image_ids.append(upload_mm_image(driver, channel_id, image, filename))

            driver.posts.create_post(options={
                'channel_id': channel_id,
                # 'message': f'*{prompt}*',
                'root_id': post['root_id'] if post['root_id'] != '' else post['id'],
                'file_ids': image_ids
            })
            db.responded_to_messages.add(post['id'])
            db.responded_to_threads.add(post['channel_id']+"-"+post['root_id'])
            db.save()


def extract_prompt(message: str, username: str) -> str:
    ''' Extracts the prompt from the message, it stripse everything before the @username and everything after the first newline following the prompt '''
    initial_index = message.index(f'@{username}') + len(f'@{username}') + 1
    message = message[initial_index:].strip()
    return message[: message.index('\n')] if '\n' in message else message


def shall_i_respond(my_user: dict, post: dict) -> bool:
    ''' Checks if the bot should respond to the message. If author is in a list of prohibited authors it will return False
     If the message does not contain the bot's username it will return False and if the author is in the list of only 1 reply list, and is already there
     it will return False'''
    if post.get('user_id') == my_user['id']:
        return False
    if f'@{my_user["username"]}' not in post.get('message'):
        return False
    if post['id'] in db.responded_to_messages:
        return False
    if post.get('username') in NO_RESPONSE_USERNAMES:
        return False
    if post.get('username') in ONCE_ONLY_RESPONSE_USERNAMES and post['id'] in db.responded_to_threads:
        return False
    return True


def get_unread_posts(mm_driver: Driver, my_user: dict) -> None:
    ''' Gets the unread posts from all channels and yields them '''
    # Get the user's teams
    teams = mm_driver.teams.get_user_teams(my_user['id'])

    # Iterate through the teams
    for team in teams:
        # Get the team's channels
        channels = mm_driver.channels.get_channels_for_user(my_user['id'], team['id'])

        # Iterate through the channels
        for channel in channels:
            # Get the unread posts
            unread_posts = mm_driver.posts.get_unread_posts_for_channel(my_user['id'], channel['id'], params={"unread": True, "since": db.last_check_ts})

            for key, post in unread_posts["posts"].items():
                yield post
        db.check()


def fetch_and_process_unread_posts(mm_driver: Driver, my_user: dict) -> None:
    ''' Fetches the unread posts and processes them '''
    for post in get_unread_posts(mm_driver, my_user):
        process_post(mm_driver, my_user, post)
    threading.Timer(600, fetch_and_process_unread_posts, kwargs={"mm_driver":mm_driver, "my_user":my_user}).start()  # Schedule the job to run every 5 minutes (300 seconds)



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
            process_post(driver, my_user, post)

    fetch_and_process_unread_posts(driver, my_user)

    driver.init_websocket(handle_event)


if __name__ == '__main__':
    main()