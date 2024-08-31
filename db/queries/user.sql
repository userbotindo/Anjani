-- name: GetUserById :one
SELECT * FROM public.user WHERE user_id = $1;

-- name: CreateUser :one
INSERT INTO public.user (user_id, username, hash, is_started, last_seen)
VALUES ($1, $2, $3, $4, now())
RETURNING *;

-- name: UpsertUserById :one
INSERT INTO public.user (user_id, username, is_started, last_seen)
VALUES ($1, $2, $3, now())
ON CONFLICT (user_id) DO UPDATE
SET user_id = $1, username = $2, is_started = $3, last_seen = now()
RETURNING *;

