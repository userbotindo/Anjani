# Anjani

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/dea98029aaf248538a413e26aa2a194a)](https://www.codacy.com/gh/userbotindo/Anjani/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=userbotindo/Anjani&amp;utm_campaign=Badge_Grade)

A modular Telegram group management bot running with Python based on [Pyrogram](https://github.com/pyrogram/pyrogram).

Ca be found on Telegram as [Anjani](https://t.me/dAnjani_bot)

Help us to cover more languages by contributin translation in [Crowdin](https://crowdin.com/project/anjani-bot)!


## Requirements
 - Python 3.8 or higher (recomended).
 - [Telegram API key](https://docs.pyrogram.org/intro/setup#api-keys).
 - [Telegram Bot Token](https://t.me/botfather)
 - [MongoDB Database](https://cloud.mongodb.com/).


## Set Up

### Configuration
Set up your bot configuration variables by renaming `confing.env_sample` to `config.env` and edit it with your own values.

### Dependencies
Install all required dependencies by running
`pip3 install -r requirements.txt`.

### Run
Once everyting set up, start the client by running
`python3 -m anjani_bot`

## Plugin

### Creating your own Modules

We try our best to simplify module creation.

All you need is a `<plugin-name>.py` file in `anjani_bot/plugins`.

Import the Client `from .. import anjani, plugins`.

Create a class that inherit with `plugins.Plugins` And give that Class name attribute to name the plugin. eg:

```python
from .. import anjani, plugin

class PluginClass(plugin.Plugin):
    name = "plugin name"
    helpable = True
```

Then to add a handler use a decorator `@anjani.on_command("<trigger>")` or other update handler. Command Trigger can be a `string` or a `list of strings`.

The `__migrate__()` function is used for migrating chats - when a chat is upgraded to a supergroup, the ID changes, so it is necessary to migrate it in the DB.

Define a `boolean` class variable named `helpable` which shows that the plugin has a helper (documentation) to the `/help` command. Then you can make the string on `anjani_bot/core/languages` with `{name}-help` and `{name}-button` key. `name` here is the value of the name ClassVar.


## Credits

  - [All Contributors 👥](https://github.com/userbotindo/Anjani/graphs/contributors)
