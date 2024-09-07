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
	user, err := up.q.GetUserById(context.Background(), id)
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
	log.Debug().Msgf("[upsertUser] %d", id)
	ctx := context.Background()
	tx, err := up.db.Begin(ctx)
	if err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[upsertUser] Error starting transaction")
		return nil, err
	}
	defer tx.Rollback(ctx)
	qtx := up.q.WithTx(tx)

	hash, err := util.HashMd5(id, bot.Username)
	if err != nil {
		log.Error().Err(err).Msg("[upsertUser] Error hashing user id")
		return nil, err
	}
	p := db.UpsertUserByIdParams{
		UserID:    id,
		Username:  username,
		IsStarted: hasStarted,
		Hash:      &hash,
	}
	if hasStarted != nil {
		p.IsStarted = hasStarted
	}
	user, err := qtx.UpsertUserById(context.Background(), p)
	if err != nil {
		log.Error().Err(err).Msg("[upsertUser] Error creating user")
		return nil, err
	}

	if err := tx.Commit(ctx); err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[upsertUser] Error committing transaction")
		return nil, err
	}
	return &user, nil
}

func (up *userPlugin) getChat(id int64) (*db.Chat, error) {
	user, err := up.q.GetChatById(context.Background(), id)
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
	log.Debug().Msgf("[upsertChat] %d", id)
	ctx := context.Background()
	tx, err := up.db.Begin(ctx)
	if err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[upsertChat] Error starting transaction")
		return nil, err
	}
	defer tx.Rollback(ctx)
	qtx := up.q.WithTx(tx)

	hash, err := util.HashMd5(id, bot.Username)
	if err != nil {
		log.Error().Err(err).Msg("[upsertUser] Error hashing chat id")
		return nil, err
	}
	p := db.UpsertChatByIdParams{
		ChatID:      id,
		Title:       title,
		Type:        cType,
		Hash:        &hash,
		IsForum:     isForum,
		IsBotMember: isMember,
	}
	chat, err := qtx.UpsertChatById(context.Background(), p)
	if err != nil {
		log.Error().Err(err).Msg("[upsertUser] Error creating chat")
		return nil, err
	}

	if err := tx.Commit(ctx); err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[upsertUser] Error committing transaction")
		return nil, err
	}
	return &chat, nil
}

func (up *userPlugin) upsertChatMember(chatId int64, userId int64) error {
	ctx := context.Background()
	tx, err := up.db.Begin(ctx)
	if err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[upsertChatMember] Error starting transaction")
	}
	defer tx.Rollback(ctx)
	qtx := up.q.WithTx(tx)

	_, err = qtx.UpsertChatMember(context.Background(), db.UpsertChatMemberParams{
		ChatID: chatId,
		UserID: userId,
	})
	if err != nil {
		log.Error().Err(err).Msg("[upsertChatMember] Error upserting chat member")
		return err
	}

	if err := tx.Commit(ctx); err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[upsertChatMember] Error committing transaction")
		return err
	}
	return nil
}

func (up *userPlugin) migrateChat(newId int64, oldId int64) error {
	ctx := context.Background()
	tx, err := up.db.Begin(ctx)
	if err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[migrateChatMember] Error starting transaction")
	}
	defer tx.Rollback(ctx)
	qtx := up.q.WithTx(tx)

	_, err = qtx.MigrateChatId(context.Background(), db.MigrateChatIdParams{
		NewChatID: newId,
		OldChatID: oldId,
	})
	if err != nil {
		log.Error().Err(err).Msg("[migrateChatMember] Error migrating chat")
		return err
	}

	_, err = qtx.MigrateChatMemberChatId(context.Background(), db.MigrateChatMemberChatIdParams{
		NewChatID: newId,
		OldChatID: oldId,
	})
	if err != nil {
		log.Error().Err(err).Msg("[migrateChatMember] Error migrating chat member")
		return err
	}

	if err := tx.Commit(ctx); err != nil {
		log.Error().Err(err).Ctx(ctx).Msg("[migrateChatMember] Error committing transaction")
		return err
	}
	return nil
}
