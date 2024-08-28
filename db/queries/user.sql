-- name: GetUserById :one
SELECT * FROM public.user WHERE user_id = $1;
