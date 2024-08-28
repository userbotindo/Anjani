-- +goose Up
-- +goose StatementBegin
CREATE TABLE IF NOT EXISTS public.chat (
    id serial primary key,
    chat_id integer not null unique,
    title varchar(255) not null,
    type varchar(20) not null,
    is_bot_member boolean not null default false,
    last_update timestamp not null default current_timestamp
);

CREATE TABLE IF NOT EXISTS public.user (
    user_id integer primary key,
    username varchar(35) not null,
    hash varchar(32) not null,
    is_started boolean default false,
    last_seen timestamp not null default current_timestamp
);

CREATE TABLE IF NOT EXISTS public.chat_setting (
    chat_id integer primary key references public.chat(chat_id),
    language varchar(5) default 'en',
    rules text,
    action_topic integer,
    spam_detection_setting boolean default true,
    warn_limit integer default 3
);

CREATE TABLE IF NOT EXISTS public.user_setting (
    user_id integer primary key references public.user(user_id),
    rank varchar(20) default 'user',
    language varchar(5) default 'en'
);


CREATE TABLE IF NOT EXISTS public.greeting (
    chat_id integer primary key references public.chat(chat_id),
    clean_service boolean default false,
    welcome_message text,
    goodbye_message text,
    file_id text,
    prev_welcome_id integer,
    prev_goodbye_id integer,
    should_welcome boolean default false,
    should_goodbye boolean default false,
    type integer default 0
);


-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS public.chat_setting;

DROP TABLE IF EXISTS public.user_setting;

DROP TABLE IF EXISTS public.greeting;

DROP TABLE IF EXISTS public.chat;

DROP TABLE IF EXISTS public.user;
-- +goose StatementEnd
