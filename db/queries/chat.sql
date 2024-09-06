-- name: GetChatById :one
SELECT * FROM public.chat WHERE chat_id = $1;


-- name: UpsertChatById :one
INSERT INTO public.chat (chat_id, title, type, is_forum, is_bot_member, hash, last_update)
VALUES ($1, $2, $3, $4, $5, $6, now())
ON CONFLICT (chat_id)
DO UPDATE
SET title = EXCLUDED.title,
    type = EXCLUDED.type,
    is_forum = EXCLUDED.is_forum,
    is_bot_member = EXCLUDED.is_bot_member,
    last_update = now()
RETURNING *;

