from typing import TYPE_CHECKING, Any, MutableMapping

from pyrogram import Client
from pyrogram import errors
from pyrogram.filters import Filter, create
from pyrogram.types import Message

from .anjani_mixin_base import MixinBase
from anjani import command, plugin, util

if TYPE_CHECKING:
    from .anjani_bot import Anjani


class CommandDispatcher(MixinBase):
    # Initialized during instantiation
    commands: MutableMapping[str, command.Command]

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        # Initialize command map
        self.commands = {}

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def register_command(
        self: "Anjani", plug: plugin.Plugin, name: str, func: command.CommandFunc
    ) -> None:
        cmd = command.Command(name, plug, func)

        if name in self.commands:
            orig = self.commands[name]
            raise plugin.ExistingCommandError(orig, cmd)

        self.commands[name] = cmd

        for alias in cmd.aliases:
            if alias in self.commands:
                orig = self.commands[alias]
                raise plugin.ExistingCommandError(orig, cmd, alias=True)

            self.commands[alias] = cmd

    def unregister_command(self: "Anjani", cmd: command.Command) -> None:
        del self.commands[cmd.name]

        for alias in cmd.aliases:
            try:
                del self.commands[alias]
            except KeyError:
                continue

    def register_commands(self: "Anjani", plug: plugin.Plugin) -> None:
        for name, func in util.misc.find_prefixed_funcs(plug, "cmd_"):
            done = False

            try:
                self.register_command(plug, name, func)
                done = True
            finally:
                if not done:
                    self.unregister_commands(plug)

    def unregister_commands(self: "Anjani", plug: plugin.Plugin) -> None:
        # Can't unregister while iterating, so collect commands to unregister afterwards
        to_unreg = []

        for name, cmd in self.commands.items():
            # Let unregister_command deal with aliases
            if name != cmd.name:
                continue

            if cmd.plugin == plug:
                to_unreg.append(cmd)

        # Actually unregister the commands
        for cmd in to_unreg:
            self.unregister_command(cmd)

    def command_predicate(self: "Anjani") -> Filter:

        async def func(flt, client: Client, message: Message) -> bool:  # skipcq: PYL-W0613
            if message.text is not None and message.text.startswith("/"):
                parts = message.text.split()
                parts[0] = parts[0][1 :]

                # Check if bot command contains a valid username
                # eg: /ping@dAnjani_bot will return True
                # If current bot instance is dAnjani_bot else False
                username = self.user.username
                if username in parts[0]:
                    parts[0] = parts[0].replace(f"@{username}", "")

                # Check command filters
                try:
                    cmd = self.commands[parts[0]]
                except KeyError:
                    return False

                if cmd.filters:
                    permitted: bool = await cmd.filters(client, message)
                    if not permitted:
                        return False

                message.command = parts
                return True

            return False
        return create(func, "CustomCommandFilter")

    async def on_command(self: "Anjani",
                         client: Client,  # skipcq: PYL-W0613
                         message: Message) -> None:
        cmd = None

        if message.via_bot:
            return

        try:
            cmd = self.commands[message.command[0]]

            # Construct invocation context
            ctx = command.Context(
                self,
                message,
                1 + len(message.command[0]) + 1,
            )

            # Ensure specified argument needs are met
            if cmd.usage is not None and not ctx.input:
                err_base = f"⚠️ Missing parameters: {cmd.usage}"

                if cmd.usage_reply:
                    if message.reply_to_message:
                        reply_msg = message.reply_to_message
                        if reply_msg.text:
                            ctx.input = reply_msg.text
                        elif not cmd.usage_optional:
                            await ctx.respond(
                                f"{err_base}\n__The message you replied to doesn't contain text.__"
                            )
                            return
                    elif not cmd.usage_optional:
                        await ctx.respond(f"{err_base} (replying is also supported)")
                        return
                elif not cmd.usage_optional:
                    await ctx.respond(err_base)
                    return

            # Invoke command function
            try:
                ret = await cmd.run(ctx)

                # Response shortcut
                if ret is not None:
                    await ctx.respond(ret)
            except errors.MessageNotModified:
                cmd.plugin.log.warning(
                    f"Command '{cmd.name}' triggered a message edit with no changes; make sure there is only a single bot instance running"
                )
            except Exception as e:
                cmd.plugin.log.error(f"Error in command '{cmd.name}'", exc_info=e)
                await ctx.respond(
                    f"⚠️ Error executing command:\n```{util.error.format_exception(e)}```"
                )

            await self.dispatch_event("command", cmd, message)
        except Exception as e:
            if cmd is not None:
                cmd.plugin.log.error("Error in command handler", exc_info=e)

            await self.respond(
                message,
                f"⚠️ Error in command handler:\n```{util.error.format_exception(e)}```",
            )