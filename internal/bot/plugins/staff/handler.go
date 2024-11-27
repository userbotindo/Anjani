package staff

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
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

func (sp *staffPlugin) GetName() string {
	return sp.Name
}

func (sp *staffPlugin) RegisterHandler(d *ext.Dispatcher) {
	d.AddHandler(handlers.NewCommand("debug", sp.cmdDebug))
}
