# Anjani

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![DeepSource](https://deepsource.io/gh/userbotindo/Anjani.svg/?label=active+issues)](https://deepsource.io/gh/userbotindo/Anjani/?ref=repository-badge)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/dea98029aaf248538a413e26aa2a194a)](https://www.codacy.com/gh/userbotindo/Anjani/dashboard?utm_source=github.com&utm_medium=referral&utm_content=userbotindo/Anjani&utm_campaign=Badge_Grade)

A modular Telegram group management bot running with Python based on [Pyrogram](https://github.com/pyrogram/pyrogram).

Can be found on Telegram as [Anjani](https://t.me/dAnjani_bot).


## Requirements

- Python 3.8 or higher (recomended).
- [Telegram API key](https://docs.pyrogram.org/intro/setup#api-keys).
- [Telegram Bot Token](https://t.me/botfather)
- [MongoDB Database](https://cloud.mongodb.com/).

# Set Up

## Configuration

Set up your bot configuration variables by renaming `config.env_sample` to `config.env` and edit it with your values.

Configuration must be done before running the bot, otherwise it will fail to run.

## Dependencies

### Install all required dependencies by running

`python3 -m pip install -r requirements.txt`.

### Install the bot along with depencies by running

`python3 -m pip install .`

#### Error: Directory '.' is not installable. File 'setup.py' not found.

This common error is caused by an outdated version of pip. This is a relatively new standard, so a newer version of pip is necessary to make it work.

Upgrade to pip 19 to fix this issue: `pip3 install -U pip`

## Run

Once everything set up, start the client by running

`python3 -m anjani`

## Plugin

If you want to make your custom plugins, refer to [Anjani's Wiki](https://github.com/userbotindo/Anjani/wiki). It has a lot of important things to read and a plugin example to guide you.

## Credits

- [Marie](https://github.com/PaulSonOfLars/tgbot)
- [Pyrobud](https://github.com/kdrag0n/pyrobud)
- [All Contributors 👥](https://github.com/userbotindo/Anjani/graphs/contributors)
