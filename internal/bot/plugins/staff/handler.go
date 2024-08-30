package staff

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/rs/zerolog/log"
)

type staffPlugin struct {
	Name     string
	Helpable bool
}

func NewStaffPlugin() *staffPlugin {
	return &staffPlugin{
		Name:     "Staff",
		Helpable: false,
	}
}

func (sp *staffPlugin) RegisterHandler(d *ext.Dispatcher) {
	log.Info().Msgf("Registering %s Plugin", sp.Name)

	d.AddHandler(handlers.NewCommand("debug", sp.cmdDebug))
}
