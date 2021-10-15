from typing import TYPE_CHECKING, Any, Iterable, Protocol, TypeVar

from pyrogram.filters import Filter
from pyrogram.types import ChatMember

if TYPE_CHECKING:
    from anjani.core import Anjani

TypeData = TypeVar("TypeData", covariant=True)


class CustomFilter(Filter):  # skipcq: PYL-W0223
    anjani: "Anjani"
    include_bot: bool


class MemberPermissions:
    def __init__(self, delegate: ChatMember) -> None:
        self.user = delegate.user
        self.status = delegate.status
        self.title = delegate.title
        self.until_date = delegate.until_date
        self.joined_date = delegate.joined_date
        self.invited_by = delegate.invited_by
        self.promoted_by = delegate.promoted_by
        self.restricted_by = delegate.restricted_by
        self.is_member = delegate.is_member
        self.is_anonymous = delegate.is_anonymous

        self.can_be_edited = delegate.can_be_edited
        self.can_manage_chat = delegate.can_manage_chat
        self.can_post_messages = delegate.can_post_messages
        self.can_edit_messages = delegate.can_edit_messages
        self.can_delete_messages = delegate.can_delete_messages
        self.can_restrict_members = delegate.can_restrict_members
        self.can_promote_members = delegate.can_promote_members
        self.can_change_info = delegate.can_change_info
        self.can_invite_users = delegate.can_invite_users
        self.can_pin_messages = delegate.can_pin_messages
        self.can_manage_voice_chats = delegate.can_manage_voice_chats

        self.can_send_messages = delegate.can_send_messages
        self.can_send_media_messages = delegate.can_send_media_messages
        self.can_send_stickers = delegate.can_send_stickers
        self.can_send_animations = delegate.can_send_animations
        self.can_send_games = delegate.can_send_games
        self.can_use_inline_bots = delegate.can_use_inline_bots
        self.can_add_web_page_previews = delegate.can_add_web_page_previews
        self.can_send_polls = delegate.can_send_polls


class NDArray(Protocol[TypeData]):
    def __getitem__(self, key: int) -> Any: ...  # skipcq: PTC-W0049
    @property
    def size(self) -> int: ...  # skipcq: PTC-W0049


class Pipeline(Protocol):
    def predict(self, X: Iterable[Any], **predict_params: Any) -> NDArray[Any]: ...  # skipcq: PTC-W0049
    def predict_proba(self, X: Iterable[Any]) -> NDArray[Any]: ...  # skipcq: PTC-W0049
