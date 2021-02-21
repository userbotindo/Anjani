# Anjani

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/dea98029aaf248538a413e26aa2a194a)](https://www.codacy.com/gh/userbotindo/Anjani/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=userbotindo/Anjani&amp;utm_campaign=Badge_Grade)
[![Crowdin](https://badges.crowdin.net/anjani-bot/localized.svg)](https://crowdin.com/project/anjani-bot)

A modular Telegram group management bot running with Python-based on [Pyrogram](https://github.com/pyrogram/pyrogram).

Ca be found on Telegram as [Anjani](https://t.me/dAnjani_bot)

Help us to cover more languages by contributing translation in [Crowdin](https://crowdin.com/project/anjani-bot)!


## Requirements
 - Python 3.8 or higher (recomended).
 - [Telegram API key](https://docs.pyrogram.org/intro/setup#api-keys).
 - [Telegram Bot Token](https://t.me/botfather)
 - [MongoDB Database](https://cloud.mongodb.com/).


## Set Up

### Configuration
Set up your bot configuration variables by renaming `config.env_sample` to `config.env` and edit it with your values.

### Dependencies
Install all required dependencies by running
`pip3 install -r requirements.txt`.

### Run
Once everything set up, start the client by running
`python3 -m anjani_bot`

## Plugin

### Creating your Modules

We try our best to simplify module creation.

All you need is a `<plugin-name>.py` file in `anjani_bot/plugins`.

Import the Listener and plugin base `from anjani_bot import listener, plugin`.

Create a class that inherits with `plugin.Plugin` And give that Class name attribute to name the plugin. eg:

```python
from anjani_bot import listener, plugin

class PluginClass(plugin.Plugin):
    name = "plugin-name"  # Mandatory variable this plugin has a help string
    helpable = True  # Only create this if the module have a help string

    # class function that don't need decorator
    # This sometimes need to simplify your main plugin
    async def hi(self, chat_id):
        # self have the client too!
        await self.bot.client.send_message(
            chat_id=chat_id,
            text=f"Hi again i'm {self.bot.name}",  # self.bot refer to `~Anjani`
        )
        # self.bot.client refer to `~pyrogram.Client`

    @listener.on("hello", filters=filter) # filters `~pyrogram.Filters` is Optional
    async def hello(self, message):
        await message.reply_text("Hi...")
        await self.hi(message.chat.id) # refer to other class function
```

*Notes:
 - The handler function takes class instance and message.
 - You can access the bot attribute (`Anjani` instance) on `self.bot`.
 - You can access the `~pyrogram.Client` too on `self.bot.client`

### Another Method & Attributes

Define a `boolean` class variable named `helpable` which shows that the plugin has a helper (documentation) to the `/help` command. Then you can make the string on `anjani_bot/core/languages` with `{name}-help` and `{name}-button` key. `name` here is the value of the name variable on the plugin class.

The `on_load()` *(coroutine) function is called when the plugin loaded on the startup. This method only takes the class instance. You can use this to load the database collection on the plugin.

To use the bot multi languages, all you need is to use `await self.bot.text(chat_id, "<keyword>", *args, **kwargs)`. `keyword` is the string keyword on the language file (`anjani_bot/core/languages`). and you can simply put any args or kwargs that should be formatted and inserted in the string.

The `__migrate__()` *(coroutine) function is used for migrating chats - when a chat is upgraded to a supergroup, the ID changes, so it is necessary to migrate it in the DB. This method takes 3 parameters instance of the class, old chat id and new chat id eg:`self, old_chat, new_chat`.


## Credits

  - [All Contributors 👥](https://github.com/userbotindo/Anjani/graphs/contributors)
