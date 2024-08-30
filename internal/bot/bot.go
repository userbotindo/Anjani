package bot

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/rs/zerolog/log"
	plugins "github.com/userbotindo/anjani/internal/bot/plugins"
	"github.com/userbotindo/anjani/internal/common/config"
)

func createDispatcher(b *gotgbot.Bot) *ext.Updater {
	dispatcher := ext.NewDispatcher(&ext.DispatcherOpts{
		Error: func(_ *gotgbot.Bot, _ *ext.Context, err error) ext.DispatcherAction {
			log.Error().Err(err).Msg("an error occurred while handling update")
			return ext.DispatcherActionNoop
		},
		MaxRoutines: ext.DefaultMaxRoutines,
	})

	plugins.LoadPlugin(dispatcher)

	updater := ext.NewUpdater(dispatcher, nil)
	log.Info().Msg("polling started")
	updater.StartPolling(b, &ext.PollingOpts{DropPendingUpdates: true})
	return updater
}

func Run(cfg *config.Config, bot *gotgbot.Bot) *ext.Updater {
	return createDispatcher(bot)
}
