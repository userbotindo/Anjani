from typing import TYPE_CHECKING, Any, Callable, Coroutine

import pyrogram
from pyrogram.filters import Filter, create
from pyrogram.types import Message

if TYPE_CHECKING:
    from .core import Anjani

FilterFunc = Callable[[Filter, pyrogram.Client, Message],
                      Coroutine[Any, Any, bool]]


def chat_action() -> Filter:

    async def func(_: Filter, __: pyrogram.Client, chat: Message) -> bool:
        return bool(chat.new_chat_members or
                    chat.left_chat_member)

    return create(func, "CustomChatActionFilter")


def staff_only(anjani: "Anjani") -> FilterFunc:

    async def func(_: Filter, __: pyrogram.Client, message: Message) -> bool:
        user = message.from_user
        return bool(user.id in anjani.staff)

    return func
