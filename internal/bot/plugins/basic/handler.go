package basic

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/rs/zerolog/log"
)

type basicPlugin struct {
	Name     string
	Helpable bool
}

func NewBasicPlugin() *basicPlugin {
	return &basicPlugin{
		Name:     "Main",
		Helpable: true,
	}
}

func (bh *basicPlugin) RegisterHandler(d *ext.Dispatcher) {
	log.Info().Msgf("Registering %s Plugin", bh.Name)

	d.AddHandler(handlers.NewCommand("ping", bh.cmdPing))
}
