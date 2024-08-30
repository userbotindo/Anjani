package plugins

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/bot/plugins/basic"
	"github.com/userbotindo/anjani/internal/bot/plugins/staff"
)

type Plugin interface {
	RegisterHandler(d *ext.Dispatcher)
}

func loadPluginHandlers(d *ext.Dispatcher, p []Plugin) {
	for _, plugin := range p {
		plugin.RegisterHandler(d)
	}
}

func LoadPlugin(d *ext.Dispatcher) {
	log.Info().Msg("Registering Plugins")

	basicPlugin := basic.NewBasicPlugin()
	staffPlugin := staff.NewStaffPlugin()

	plugins := []Plugin{
		basicPlugin,
		staffPlugin,
	}
	loadPluginHandlers(d, plugins)
}
