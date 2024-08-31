package user

import (
	"context"

	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/common/util"
	"github.com/userbotindo/anjani/internal/db"
)

func (up *userPlugin) upsertUser(bot *gotgbot.Bot, id int64, username string, hasStarted *bool) (*db.User, error) {
	ctx := context.Background()

	var userExists bool
	if _, err := up.DB.GetUserById(ctx, id); err != nil {
		userExists = false
	} else {
		userExists = true
	}

	if userExists {
		log.Info().Msgf("Upserting User %d", id)
		p := db.UpsertUserByIdParams{
			UserID:   id,
			Username: username,
		}
		if hasStarted != nil {
			p.IsStarted = hasStarted
		}
		user, err := up.DB.UpsertUserById(ctx, p)
		if err != nil {
			log.Error().Err(err).Msg("Error upserting user")
			return nil, err
		}
		return &user, nil
	}

	log.Info().Msgf("Creating User %d", id)
	hash, err := util.HashMd5(id, bot.Username)
	if err != nil {
		log.Error().Err(err).Msg("Error hashing user id")
		return nil, err
	}
	p := db.CreateUserParams{
		UserID:    id,
		Username:  username,
		IsStarted: hasStarted,
		Hash:      &hash,
	}
	if hasStarted != nil {
		p.IsStarted = hasStarted
	}
	user, err := up.DB.CreateUser(ctx, p)
	if err != nil {
		log.Error().Err(err).Msg("Error creating user")
		return nil, err
	}
	return &user, nil
}
