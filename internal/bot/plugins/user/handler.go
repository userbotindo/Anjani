package user

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers/filters/message"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/zerolog/log"
	database "github.com/userbotindo/anjani/internal/db"
)

type userPlugin struct {
	Name     string
	Helpable bool
	db       *pgxpool.Pool
	q        *database.Queries
}

func NewUserPlugin(db *pgxpool.Pool) *userPlugin {
	return &userPlugin{
		Name:     "User",
		Helpable: true,
		q:        database.New(db),
		db:       db,
	}
}

func (up *userPlugin) RegisterHandler(d *ext.Dispatcher) {
	log.Info().Msgf("Registering %s Plugin", up.Name)

	d.AddHandler(handlers.NewCommand("info", up.cmdInfo))

	d.AddHandler(handlers.NewMessage(message.All, up.onMessage))
	d.AddHandler(handlers.NewMessage(message.Migrate, up.onMigrate))
}
