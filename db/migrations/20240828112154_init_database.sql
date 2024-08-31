-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS public.chat (
    id serial primary key,
    chat_id bigint not null unique,
    title varchar(255) not null,
    type varchar(20) not null,
    is_forum boolean not null default false,
    is_bot_member boolean not null default false,
    hash varchar(32),
    last_update timestamp without time zone default CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS chat_hash_ix ON public.chat (hash);

CREATE TABLE IF NOT EXISTS public.user (
    user_id bigint primary key,
    username varchar(35) not null,
    hash varchar(32),
    is_started boolean default false,
    reputation double precision default 0,
    last_seen timestamp without time zone default CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS user_hash_ix ON public.user (hash);
CREATE INDEX IF NOT EXISTS user_username_ix ON public.user (username);


CREATE TABLE IF NOT EXISTS public.chat_warning (
    warning_id serial primary key,
    count integer default 0,
    reasons text[]
);

CREATE TABLE IF NOT EXISTS public.chat_member (
    chat_id bigint references public.chat(chat_id),
    user_id bigint references public.user(user_id),
    warning_id integer references public.chat_warning(warning_id),
    primary key (chat_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.chat_setting (
    chat_id bigint primary key references public.chat(chat_id),
    language varchar(5) default 'en',
    rules text,
    action_topic integer,
    spam_detection_setting boolean default true,
    warn_limit integer default 3,
    reporting boolean default true,
    global_ban boolean default true,
    lockings text[]
);

CREATE TABLE IF NOT EXISTS public.user_setting (
    user_id bigint primary key references public.user(user_id),
    rank varchar(20) default 'user',
    language varchar(5) default 'en',
    reporting boolean default true
);


CREATE TABLE IF NOT EXISTS public.greeting (
    id serial not null primary key,
    chat_id bigint references public.chat(chat_id),
    clean_service boolean default false,
    welcome_message text,
    goodbye_message text,
    file text,
    prev_welcome_id bigint,
    prev_goodbye_id bigint,
    should_welcome boolean default false,
    should_goodbye boolean default false,
    type integer default 0
);

CREATE TABLE IF NOT EXISTS public.greeting_button (
    greeting_id integer references public.greeting(id),
    text varchar(50) not null,
    url text not null,
    is_same_line boolean default false
);

CREATE TABLE IF NOT EXISTS public.federation (
    federation_id varchar(36) primary key,
    name varchar(255) not null,
    owner_id integer not null references public.user(user_id),
    log_chat_id bigint references public.chat(chat_id)
);

CREATE TABLE IF NOT EXISTS public.federation_admin (
    federation_id varchar(36) references public.federation(federation_id),
    user_id bigint references public.user(user_id),
    primary key (federation_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.federation_ban (
    federation_id varchar(36) references public.federation(federation_id),
    user_id bigint references public.user(user_id),
    primary key (federation_id, user_id)
);

CREATE TABLE IF NOT EXISTS public.federation_chat (
    federation_id varchar(36) references public.federation(federation_id),
    chat_id bigint references public.chat(chat_id),
    primary key (federation_id, chat_id)
);

CREATE TABLE IF NOT EXISTS public.federation_subscriber (
    federation_id varchar(36) references public.federation(federation_id),
    federation_subscriber_id varchar(36) references public.federation(federation_id),
    primary key (federation_id, federation_subscriber_id)
);

CREATE TABLE IF NOT EXISTS public.note (
    id serial not null primary key,
    chat_id bigint references public.chat(chat_id),
    name varchar(255) not null,
    content text,
    file text,
    has_buttons boolean default false,
    note_type integer default 0
);

CREATE TABLE IF NOT EXISTS public.note_button (
    note_id integer references public.note(id),
    name varchar(50) not null,
    url text not null,
    is_same_line boolean default false
);

CREATE TABLE IF NOT EXISTS public.filter (
    id serial not null primary key,
    chat_id bigint references public.chat(chat_id),
    keyword varchar(255) not null,
    content text,
    type integer default 0
);

CREATE TABLE IF NOT EXISTS public.filter_button (
    filter_id integer references public.filter(id),
    text varchar(50) not null,
    url text not null,
    is_same_line boolean default false
);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS public.greeting_button;

DROP TABLE IF EXISTS public.greeting;

DROP TABLE IF EXISTS public.federation_ban;

DROP TABLE IF EXISTS public.federation_chat;

DROP TABLE IF EXISTS public.federation_subscriber;

DROP TABLE IF EXISTS public.federation_admin;

DROP TABLE IF EXISTS public.federation;

DROP TABLE IF EXISTS public.note_button;

DROP TABLE IF EXISTS public.note;

DROP TABLE IF EXISTS public.filter_button;

DROP TABLE IF EXISTS public.filter;

DROP TABLE IF EXISTS public.chat_member;

DROP TABLE IF EXISTS public.chat_warning;

DROP TABLE IF EXISTS public.chat_setting;

DROP TABLE IF EXISTS public.user_setting;

DROP TABLE IF EXISTS public.user;

DROP TABLE IF EXISTS public.chat;
-- +goose StatementEnd
