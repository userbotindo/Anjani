-- name: GetUserById :one
SELECT * FROM public.user WHERE user_id = $1;

-- name: UpsertUserById :one
INSERT INTO public.user (user_id, username, is_started)
VALUES ($1, $2, $3)
ON CONFLICT (user_id) DO UPDATE
SET username = $2, is_started = $3
RETURNING *;

