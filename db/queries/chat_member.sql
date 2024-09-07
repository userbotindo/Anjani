-- name: GetChatMemberByUserId :many
SELECT * FROM public.chat_member WHERE user_id = $1;

-- name: GetChatMemberByChatId :many
SELECT * FROM public.chat_member WHERE chat_id = $1;

-- name: GetChatMemberByChatIdAndUserId :one
SELECT * FROM public.chat_member WHERE chat_id = $1 AND user_id = $2;

-- name: UpsertChatMember :one
INSERT INTO public.chat_member (chat_id, user_id)
VALUES ($1, $2)
ON CONFLICT (chat_id, user_id) DO NOTHING
RETURNING *;

-- name: DeleteChatMember :one
DELETE FROM public.chat_member WHERE chat_id = $1 AND user_id = $2
RETURNING *;

-- name: MigrateChatMemberChatId :execrows
UPDATE public.chat_member
SET chat_id = sqlc.arg(new_chat_id)
WHERE chat_id = sqlc.arg(old_chat_id);
