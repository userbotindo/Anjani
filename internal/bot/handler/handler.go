package handler

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/bot/plugins"
)

func registerHandlers(d *ext.Dispatcher) {
	log.Info().Msg("Registering handlers")
	plugins.LoadPlugin(d)
}

func CreateDispatcher(b *gotgbot.Bot) *ext.Updater {
	dispatcher := ext.NewDispatcher(&ext.DispatcherOpts{
		Error: func(_ *gotgbot.Bot, _ *ext.Context, err error) ext.DispatcherAction {
			log.Error().Err(err).Msg("an error occurred while handling update")
			return ext.DispatcherActionNoop
		},
		MaxRoutines: ext.DefaultMaxRoutines,
	})

	registerHandlers(dispatcher)

	updater := ext.NewUpdater(dispatcher, nil)
	log.Info().Msg("polling started")
	updater.StartPolling(b, &ext.PollingOpts{DropPendingUpdates: true})
	return updater
}
