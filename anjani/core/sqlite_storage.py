import inspect
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from pyrogram.raw.types.input_peer_channel import InputPeerChannel
from pyrogram.raw.types.input_peer_chat import InputPeerChat
from pyrogram.raw.types.input_peer_user import InputPeerUser
from pyrogram.storage.sqlite_storage import get_input_peer
from pyrogram.storage.storage import Storage

# language=SQLite
SCHEMA = """
CREATE TABLE sessions
(
    dc_id     INTEGER PRIMARY KEY,
    api_id    INTEGER,
    test_mode INTEGER,
    auth_key  BLOB,
    date      INTEGER NOT NULL,
    user_id   INTEGER,
    is_bot    INTEGER
);

CREATE TABLE peers
(
    id             INTEGER PRIMARY KEY,
    access_hash    INTEGER,
    type           INTEGER NOT NULL,
    username       TEXT,
    phone_number   TEXT,
    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
);

CREATE TABLE IF NOT EXISTS usernames
(
    id             TEXT PRIMARY KEY,
    peer_id        INTEGER NOT NULL,
    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
);

CREATE TABLE version
(
    number INTEGER PRIMARY KEY
);

CREATE INDEX idx_peers_id ON peers (id);
CREATE INDEX idx_peers_username ON peers (username);
CREATE INDEX idx_peers_phone_number ON peers (phone_number);

CREATE TRIGGER trg_peers_last_update_on AFTER UPDATE ON peers
BEGIN
    UPDATE peers
    SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_session_last_update_on AFTER INSERT ON peers
BEGIN
    UPDATE sessions
    SET date = CAST(STRFTIME('%s', 'now') AS INTEGER);
END;

CREATE TRIGGER IF NOT EXISTS trg_usernames_last_update_on
    AFTER UPDATE
    ON usernames
BEGIN
    UPDATE usernames
    SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
    WHERE id = NEW.id;
END;
"""


class SQLiteStorage(Storage):
    VERSION = 4
    USERNAME_TTL = 8 * 60 * 60
    _conn: sqlite3.Connection

    def __init__(self, name: str):
        super().__init__(name)
        self.database = Path(os.getcwd()) / f"anjani/{name}.session"

    async def delete(self):
        raise NotImplementedError

    async def create(self):
        with self.conn:
            self.conn.executescript(SCHEMA)

            self.conn.execute(
                "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (2, None, None, None, 0, None, None),
            )

            self.conn.execute("INSERT INTO version VALUES (?)", (self.VERSION,))

    async def update(self):
        version = await self.version()

        if version == 3:
            with self.conn:
                self.conn.executescript(
                    """
CREATE TABLE IF NOT EXISTS usernames
(
    id             TEXT PRIMARY KEY,
    peer_id        INTEGER NOT NULL,
    last_update_on INTEGER NOT NULL DEFAULT (CAST(STRFTIME('%s', 'now') AS INTEGER))
);

CREATE TRIGGER IF NOT EXISTS trg_usernames_last_update_on
    AFTER UPDATE
    ON usernames
BEGIN
    UPDATE usernames
    SET last_update_on = CAST(STRFTIME('%s', 'now') AS INTEGER)
    WHERE id = NEW.id;
END;
"""
                )
            version += 1

        await self.version(version)  # type:ignore

    async def open(self):
        path = self.database
        file_exists = path.is_file()

        self.conn = sqlite3.connect(database=str(path), timeout=1, check_same_thread=False)

        if not file_exists:
            await self.create()
        else:
            await self.update()

        self.conn.execute("VACUUM")

    async def save(self):
        await self.date(int(time.time()))

    async def close(self):
        self.conn.close()

    async def update_peers(self, peers: List[Tuple[int, int, str, str, str]]) -> None:
        with self.conn:
            self.conn.executemany(
                "REPLACE INTO peers (id, access_hash, type, username, phone_number)"
                "VALUES (?, ?, ?, ?, ?)",
                peers,
            )

    async def update_usernames(self, usernames: List[Tuple[int, str]]):
        for user in usernames:
            self.conn.execute("DELETE FROM usernames WHERE peer_id=?", (user[0],))
        self.conn.executemany("REPLACE INTO usernames (peer_id, id)" "VALUES (?, ?)", usernames)

    async def get_peer_by_id(
        self, peer_id: int
    ) -> Union[InputPeerUser, InputPeerChat, InputPeerChannel]:
        r = self.conn.execute(
            "SELECT id, access_hash, type FROM peers WHERE id = ?", (peer_id,)
        ).fetchone()

        if r is None:
            raise KeyError(f"ID not found: {peer_id}")

        return get_input_peer(*r)

    async def get_peer_by_username(
        self, username: str
    ) -> Union[InputPeerUser, InputPeerChat, InputPeerChannel]:
        r = self.conn.execute(
            "SELECT id, access_hash, type, last_update_on FROM peers WHERE username = ?"
            "ORDER BY last_update_on DESC",
            (username,),
        ).fetchone()

        if r is None:
            r2 = self.conn.execute(
                "SELECT peer_id, last_update_on FROM usernames WHERE id = ?"
                "ORDER BY last_update_on DESC",
                (username,),
            ).fetchone()
            if r2 is None:
                raise KeyError(f"Username not found: {username}")

            if abs(time.time() - r2[1]) > self.USERNAME_TTL:
                raise KeyError(f"Username expired: {username}")
            r = r = self.conn.execute(
                "SELECT id, access_hash, type, last_update_on FROM peers WHERE id = ?"
                "ORDER BY last_update_on DESC",
                (r2[0],),
            ).fetchone()
            if r is None:
                raise KeyError(f"Username not found: {username}")

        if abs(time.time() - r[3]) > self.USERNAME_TTL:
            raise KeyError(f"Username expired: {username}")

        return get_input_peer(*r[:3])

    async def get_peer_by_phone_number(
        self, phone_number: str
    ) -> Union[InputPeerUser, InputPeerChat, InputPeerChannel]:
        q = self.conn.execute(
            "SELECT id, access_hash, type FROM peers WHERE phone_number = ?", (phone_number,)
        )
        r = q.fetchone()

        if r is None:
            raise KeyError(f"Phone number not found: {phone_number}")

        return get_input_peer(*r)

    async def _get(self) -> Optional[Any]:
        attr = inspect.stack()[2].function

        q = self.conn.execute(f"SELECT {attr} FROM sessions")
        return (q.fetchone())[0]

    async def _set(self, value: Any) -> None:
        attr = inspect.stack()[2].function
        with self.conn:
            self.conn.execute(f"UPDATE sessions SET {attr} = ?", (value,))

    async def _accessor(self, value: Any = object) -> Any:
        return await self._get() if value == object else await self._set(value)

    async def dc_id(self, value=object) -> Optional[int]:
        return await self._accessor(value)

    async def api_id(self, value=object) -> Optional[int]:
        return await self._accessor(value)

    async def test_mode(self, value=object) -> Optional[bool]:
        return await self._accessor(value)

    async def auth_key(self, value=object) -> Optional[bytes]:
        return await self._accessor(value)

    async def date(self, value=object) -> Optional[int]:
        return await self._accessor(value)

    async def user_id(self, value=object) -> Optional[int]:
        return await self._accessor(value)

    async def is_bot(self, value=object) -> Optional[bool]:
        return await self._accessor(value)

    async def version(self, value: Any = object):
        if value == object:
            q = self.conn.execute("SELECT number FROM version")
            return (q.fetchone())[0]
        else:
            with self.conn:
                self.conn.execute("UPDATE version SET number = ?", (value,))
