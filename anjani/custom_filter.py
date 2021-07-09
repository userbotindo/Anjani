from typing import Any, Callable, Coroutine

import pyrogram
from pyrogram.filters import Filter, create
from pyrogram.types import Message


FilterFunc = Callable[[Filter, pyrogram.Client, Message],
                      Coroutine[Any, Any, bool]]


def chat_action() -> Filter:

    async def func(_: Filter, __: pyrogram.Client, chat: Message) -> bool:
        return bool(chat.new_chat_members or
                    chat.left_chat_member)

    return create(func, "CustomChatActionFilter")


def _staff_only(anjani: bool = True) -> Filter:

    async def func(flt: Filter, __: pyrogram.Client, message: Message) -> bool:
        user = message.from_user
        return bool(user.id in flt.bot.staff)

    if anjani:
        return create(func, "CustomStaffFilter", anjani=True)
    
    return create(func, "CustomStaffFilter")

staff_only = _staff_only()
