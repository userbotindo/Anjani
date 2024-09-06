package plugins

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/bot/plugins/basic"
	"github.com/userbotindo/anjani/internal/bot/plugins/staff"
	"github.com/userbotindo/anjani/internal/bot/plugins/user"
)

type Plugin interface {
	RegisterHandler(d *ext.Dispatcher)
}

func loadPluginHandlers(d *ext.Dispatcher, p []Plugin) {
	for _, plugin := range p {
		plugin.RegisterHandler(d)
	}
}

func LoadPlugin(d *ext.Dispatcher, db *pgxpool.Pool) {
	log.Info().Msg("Registering Plugins")

	basicPlugin := basic.NewBasicPlugin()
	staffPlugin := staff.NewStaffPlugin()
	userPlugin := user.NewUserPlugin(db)

	plugins := []Plugin{
		basicPlugin,
		staffPlugin,
		userPlugin,
	}
	loadPluginHandlers(d, plugins)
}
