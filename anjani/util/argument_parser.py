import inspect
from functools import partial
from types import FunctionType
from typing import Any, Tuple

from anjani.command import Context


async def parse_arguments(sig: inspect.Signature, ctx: Context) -> Tuple[Any, ...]:
    message = ctx.msg
    args = []
    idx = 1
    items = iter(sig.parameters.items())
    next(items)  # skip Context argument
    for _, param in items:
        try:
            if param.annotation is param.empty:
                res = message.command[idx]
                idx += 1
            elif isinstance(param.annotation, (FunctionType, partial)):
                if inspect.iscoroutinefunction(param.annotation):
                    res = await param.annotation(ctx.input or param.default, ctx.bot.client)
                else:
                    res = param.annotation(ctx.input or param.default, ctx.bot.client)
            else:
                res = param.annotation(message.command[idx])
                idx += 1
        except IndexError:
            res = param.default if param.default is not param.empty else None
        args.append(res)
    return tuple(args)
