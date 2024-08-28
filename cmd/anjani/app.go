package main

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/rs/zerolog/log"

	"github.com/userbotindo/anjani/internal/common/config"
)

func CreateBot(cfg *config.Config) *gotgbot.Bot {
	bot, err := gotgbot.NewBot(cfg.Telegram.BotToken, &gotgbot.BotOpts{})
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to create bot")
	}

	return bot
}
