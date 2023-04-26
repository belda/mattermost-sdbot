import asyncio
import json
import ssl
from builtins import print

from mattermostdriver import Driver
import requests

bot_username = ''
bot_password = ''
server_url = ''

def main():
    driver = Driver({'url': server_url, 'port':443, 'token':'', 'scheme': 'https', 'verify': True})
    driver.login()
    my_user = driver.users.get_user('me')
    print(f"Logged in! My user is id={my_user['id']}, username={my_user['username']}")
    # team = driver.teams.get_team_by_name('team_name')
    # channel = driver.channels.get_channel_by_name(team['id'], 'channel_name')

    # @driver.on('message')
    async def handle_event(input):
        data = json.loads(input)
        if data.get('event') == 'posted':
            post = json.loads(data.get('data').get('post'))
            if post.get('user_id') == my_user['id']:
                return
            message = post.get('message')
            channel_id = post.get('channel_id')

            await asyncio.sleep(2)
            driver.posts.create_post(options={
                'channel_id': channel_id,
                'message': f'This is my response to *{message}*',
                'root_id': post['root_id'] if post['root_id'] != '' else post['id']
            })

    driver.init_websocket(handle_event)
    print("Logged in, waiting for messages...")


if __name__ == '__main__':
    main()



''' EXAMPLE REQUEST

# PING
curl 'http://192.168.18.40:9000/ping?session_id=1682002146528' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en' \
  -H 'Connection: keep-alive' \
  -H 'Referer: http://192.168.18.40:9000/' \
  -H 'Sec-GPC: 1' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36' \
  --compressed \
  --insecure
  
-> 200 OK
{"status":"Rendering","tasks":{"140578524467936":"completed","140578524470192":"running"},"devices":{"all":{"cuda:0":{"name":"NVIDIA GeForce RTX 3060 Ti","mem_free":2.319908864,"mem_total":8.360624128,"max_vram_usage_level":"high"},"cpu":{"name":"Intel(R) Xeon(R) CPU E5-2620 v4 @ 2.10GHz"}},"active":{"cuda:0":{"name":"NVIDIA GeForce RTX 3060 Ti","mem_free":2.320695296,"mem_total":8.360624128,"max_vram_usage_level":"high"}}}}
  

# RENDER
curl 'http://192.168.18.40:9000/render' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Origin: http://192.168.18.40:9000' \
  -H 'Referer: http://192.168.18.40:9000/' \
  -H 'Sec-GPC: 1' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36' \
  --data-raw '{"prompt":"man standing at the edge of a cliff looking at landscape holding paintbrush, colorful and vibrant background , sun rising in distance","seed":2036836938,"used_random_seed":true,"negative_prompt":"","num_outputs":1,"num_inference_steps":60,"guidance_scale":7.5,"width":512,"height":512,"vram_usage_level":"balanced","sampler_name":"euler_a","use_stable_diffusion_model":"sd-v1-4","use_vae_model":"","stream_progress_updates":true,"stream_image_progress":false,"show_only_filtered_image":true,"block_nsfw":false,"output_format":"jpeg","output_quality":75,"output_lossless":false,"metadata_output_format":"none","original_prompt":"man standing at the edge of a cliff looking at landscape holding paintbrush, colorful and vibrant background , sun rising in distance","active_tags":[],"inactive_tags":[],"use_face_correction":"GFPGANv1.3","use_upscale":"RealESRGAN_x4plus","upscale_amount":"4","session_id":"1682002146528"}' \
  --compressed \
  --insecure
  
  
-> 200 OK
{"status":"Online","queue":1,"stream":"/image/stream/140578524470192","task":140578524470192}

# GET THE IMAGE
curl 'http://192.168.18.40:9000/image/stream/140578524470192' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/json' \
  -H 'Referer: http://192.168.18.40:9000/' \
  -H 'Sec-GPC: 1' \
  -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36' \
  --compressed \
  --insecure
  
-> 200 OK
{"step": 33, "step_time": 0.18673157691955566, "total_steps": 60}{"step": 34, "step_time": 0.2203199863433838, "total_steps": 60}

-> 200 OK
{"status": "succeeded", "render_request": {"prompt": "man standing at the edge of a cliff looking at landscape holding paintbrush, colorful and vibrant background , sun rising in distance", "negative_prompt": "", "seed": 2036836938, "width": 512, "height": 512, "num_outputs": 1, "num_inference_steps": 60, "guidance_scale": 7.5, "prompt_strength": 0.8, "sampler_name": "euler_a", "hypernetwork_strength": 0, "lora_alpha": 0, "preserve_init_image_color_profile": false}, "task_data": {"request_id": 140578524470192, "session_id": "1682002146528", "save_to_disk_path": null, "vram_usage_level": "balanced", "use_face_correction": "/mnt/d1/belda/Downloads/stable-diffusion-ui/models/gfpgan/GFPGANv1.3.pth", "use_upscale": "/mnt/d1/belda/Downloads/stable-diffusion-ui/models/realesrgan/RealESRGAN_x4plus.pth", "upscale_amount": 4, "use_stable_diffusion_model": "/mnt/d1/belda/Downloads/stable-diffusion-ui/models/stable-diffusion/sd-v1-4.ckpt", "use_vae_model": null, "use_hypernetwork_model": null, "use_lora_model": null, "show_only_filtered_image": true, "block_nsfw": false, "output_format": "jpeg", "output_quality": 75, "output_lossless": false, "metadata_output_format": "none", "stream_image_progress": false, "stream_image_progress_interval": 5}, "output": [{"data": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL...
 +TjH40uQD060gxuxj8qEBGGx1FO3ZWnMoXgjBqLHOR0p7gSDnimScUuSuDUbsWNNIYxvXpTaX60CrGBpBS0YpgHvQTRSUAOAo4zR2pKQH//2Q==", "seed": 2036836938, "path_abs": null}]}

'''