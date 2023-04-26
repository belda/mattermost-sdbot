# Mattermost bot for Stable Diffusion UI

## Prerequisites

* [Easy Diffusion](https://github.com/cmdr2/stable-diffusion-ui/)
* Python 3.9
* Mattermost Bot account and it's token

## Running the bot
The code needs to run either in a docker container or as an app with 3.1 < python <= 3.9.

```bash
docker build -t sdbot .
``` 

Then you can run the bot with the following command:

```bash
docker run -it --rm --name sdbot-instance \
  -e MMBOT_TOKEN='bots secret token' \
  -e MM_SERVER_URL='yourmattermost server url' \
  -e SD_SERVER_URL='your stable diffusion ui server location' \
  sdbot
```

