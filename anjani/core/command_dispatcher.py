import inspect
from typing import TYPE_CHECKING, Any, Dict, List, MutableMapping

from pyrogram import Client, errors
from pyrogram.filters import Filter, create
from pyrogram.types import Message

from anjani import command, plugin, util
from anjani.error import CommandHandlerError, CommandInvokeError, ExistingCommandError
from anjani.util.converter import parse_arguments

from .anjani_mixin_base import MixinBase

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
            raise ExistingCommandError(orig, cmd)

        self.commands[name] = cmd

        for alias in cmd.aliases:
            if alias in self.commands:
                orig = self.commands[alias]
                raise ExistingCommandError(orig, cmd, alias=True)

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
        async def func(flt: Filter, client: Client, message: Message) -> bool:  # skipcq: PYL-W0613
            if message.via_bot:
                return False

            if message.text is not None and message.text.startswith("/"):
                parts = message.text.split()
                parts[0] = parts[0][1:]

                # Check if bot command contains a valid username
                # eg: /ping@dAnjani_bot will return True
                # If current bot instance is dAnjani_bot else False
                if self.user.username in parts[0]:
                    # Remove username from command
                    parts[0] = parts[0].replace(f"@{self.user.username}", "")

                # Filter if command is not in commands
                try:
                    cmd = self.commands[parts[0]]
                except KeyError:
                    return False

                # Check additional build-in filters
                if cmd.filters:
                    permitted = await cmd.filters(client, message)
                    if not permitted:
                        return False

                message.command = parts
                return True

            return False

        return create(func, "CustomCommandFilter")

    async def on_command(
        self: "Anjani", client: Client, message: Message  # skipcq: PYL-W0613
    ) -> None:
        cmd = None

        try:
            cmd = self.commands[message.command[0]]
            # Construct invocation context
            ctx = command.Context(
                self,
                message,
                1 + len(message.command[0]) + 1,
            )

            # Parse and convert handler required parameters
            signature = inspect.signature(cmd.func)
            args = []  # type: List[Any]
            kwargs = {}  # type: Dict[Any, Any]
            if len(signature.parameters) > 1:
                args, kwargs = await parse_arguments(signature, ctx, cmd.func)

            # Invoke command function
            try:
                ret = await cmd.func(ctx, *args, **kwargs)

                # Response shortcut
                if ret is not None:
                    async with ctx.action("typing"):
                        await ctx.respond(ret)
            except errors.MessageNotModified:
                cmd.plugin.log.warning(
                    "Command '%s' triggered a message edit with no changes; make sure there is only a single bot instance running",
                    cmd.name
                )
            except Exception as e:  # skipcq: PYL-W0703
                constructor_invoke = CommandInvokeError(
                    f"raised from {type(e).__name__}: {str(e)}"
                ).with_traceback(e.__traceback__)
                cmd.plugin.log.error("Error in command '%s'", cmd.name, exc_info=constructor_invoke)

            await self.dispatch_event("command", cmd, message)
        except Exception as e:  # skipcq: PYL-W0703
            constructor_handler = CommandHandlerError(
                f"raised from {type(e).__name__}: {str(e)}"
            ).with_traceback(e.__traceback__)
            if cmd is not None:
                cmd.plugin.log.error("Error in command handler", exc_info=constructor_handler)
