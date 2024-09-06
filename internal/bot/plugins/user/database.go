package user

import (
	"context"
	"errors"

	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/jackc/pgx/v5"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/common/util"
	"github.com/userbotindo/anjani/internal/db"
)

func (up *userPlugin) getUser(id int64) (*db.User, error) {
	ctx := context.Background()
	user, err := up.DB.GetUserById(ctx, id)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		log.Error().Err(err).Msg("Error getting user by id")
		return nil, err
	}
	return &user, nil
}

func (up *userPlugin) upsertUser(bot *gotgbot.Bot, id int64, username string, hasStarted *bool) (*db.User, error) {
	ctx := context.Background()

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

func (up *userPlugin) getChat(id int64) (*db.Chat, error) {
	ctx := context.Background()
	user, err := up.DB.GetChatById(ctx, id)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		log.Error().Err(err).Msg("Error getting chat by id")
		return nil, err
	}
	return &user, nil
}

func (up *userPlugin) upsertChat(bot *gotgbot.Bot, id int64, title string, cType string, isForum bool, isMember *bool) (*db.Chat, error) {
	ctx := context.Background()

	log.Info().Msgf("Creating Chat %d", id)
	hash, err := util.HashMd5(id, bot.Username)
	if err != nil {
		log.Error().Err(err).Msg("Error hashing chat id")
		return nil, err
	}
	p := db.CreateChatParams{
		ChatID:      id,
		Title:       title,
		Type:        cType,
		Hash:        &hash,
		IsForum:     isForum,
		IsBotMember: isMember,
	}
	chat, err := up.DB.CreateChat(ctx, p)
	if err != nil {
		log.Error().Err(err).Msg("Error creating chat")
		return nil, err
	}
	return &chat, nil
}
