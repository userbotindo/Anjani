-- name: GetUserById :one
SELECT * FROM public.user WHERE user_id = $1;


-- name: UpsertUserById :one
INSERT INTO public.user (user_id, username, hash, is_started, last_seen)
VALUES ($1, $2, $3, $4, now())
ON CONFLICT (user_id) DO UPDATE
SET username = EXCLUDED.username,
    is_started = EXCLUDED.is_started,
    last_seen = now()
RETURNING *;
