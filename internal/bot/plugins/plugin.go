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
	GetName() string
}

var plugins []Plugin

func getAllPlugins() []string {
	// yield all plugins
	var all []string
	for _, plugin := range plugins {
		all = append(all, plugin.GetName())

	}
	return all
}

func LoadPlugin(d *ext.Dispatcher, db *pgxpool.Pool) {
	log.Info().Msg("Registering Plugins")

	plg := []Plugin{
		basic.NewBasicPlugin(getAllPlugins),
		staff.NewStaffPlugin(),
		user.NewUserPlugin(db),
	}

	for _, p := range plg {
		log.Info().Msgf("Registering Plugin: %s", p.GetName())
		p.RegisterHandler(d)
	}

	plugins = plg
}
