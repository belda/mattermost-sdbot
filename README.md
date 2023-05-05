# Mattermost bot for Stable Diffusion UI

This is a bot for Mattermost that can be used to interact with the Stable Diffusion UI (Easy Diffusion). 
It renders images based on your prompt and sends them to the Mattermost channel you call the bot from.

## Usage

1. Have your Mattermost server set up and running
2. Create a bot account (see [Mattermost documentation](https://docs.mattermost.com/developer/bot-accounts.html))
3. Add it to the relevant channels
4. Install and run Easy Diffusion
5. Run the bot (see below)
6. Call the bot from the channel with by mentioning it and providing a prompt

![example_screenshot.png](docs%2Fexample_screenshot.png)


## Prerequisites

* [Easy Diffusion](https://github.com/cmdr2/stable-diffusion-ui/)
* Python 3.9
* Mattermost Bot account and it's token

## Running the bot
The code needs to run either in a docker container or as an app with 3.1 < python <= 3.9.


### Directly

You can run the bot directly with the following command:
```bash
MMBOT_TOKEN="your_bot_secret token" MM_SERVER_URL="your_mattermost_server_url" SD_SERVER_URL="your_sd_server_url" python3 sdbot.py
```


### Docker way

Build the image and create a volume for the data file:

```bash
docker build -t sdbot .
docker volume create mattermost-sdbot-data
``` 

Then you can run the bot with the following command:

```bash
docker run -it --rm --name sdbot-instance \
  -v /tmp/sdbot:/app/data \
  -e DATA_FILE='/app/data/data.pickle' \
  -e MMBOT_TOKEN='bots secret token' \
  -e MM_SERVER_URL='yourmattermost server url' \
  -e SD_SERVER_URL='your stable diffusion ui server location' \
  sdbot
```


## Options

The bot can be configured with the following environment variables:

| Variable | Description                                                                                                     | Default       | Optional |
| --- |-----------------------------------------------------------------------------------------------------------------|---------------| --- |
| DATA_FILE | Path to the data file that keeps track of what was responded to                                                 | ./data.pickle | yes |
| MMBOT_TOKEN | The token of the Mattermost bot account                                                                         | -             | no |
| MM_SERVER_URL | The URL of the Mattermost server                                                                                | -             | no |
| SD_SERVER_URL | The URL of the Stable Diffusion UI server                                                                       | -             | no |
| BATCH_SIZE | The number of images to generate in one batch                                                                   | 4             | yes |
| NO_RESPONSE_USERNAMES | A comma separated list of usernames that should not be responded to                                             | -             | yes |
| ONCE_ONLY_RESPONSE_USERNAMES | A comma separated list of usernames that should only be responded to once (to avoid bots chatting to each other | chatgpt       | yes |

