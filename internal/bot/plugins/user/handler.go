package user

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers/filters/message"
	"github.com/rs/zerolog/log"
	database "github.com/userbotindo/anjani/internal/db"
)

type userPlugin struct {
	Name     string
	Helpable bool
	DB       *database.Queries
}

func NewUserPlugin(db database.DBTX) *userPlugin {
	return &userPlugin{
		Name:     "User",
		Helpable: true,
		DB:       database.New(db),
	}
}

func (up *userPlugin) RegisterHandler(d *ext.Dispatcher) {
	log.Info().Msgf("Registering %s Plugin", up.Name)

	d.AddHandler(handlers.NewCommand("info", up.cmdInfo))

	d.AddHandler(handlers.NewMessage(message.All, up.onMessage))
}
