package basic

import (
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers/filters/callbackquery"
)

type basicPlugin struct {
	Name         string
	Helpable     bool
	getAllPlugin func() []string
}

func NewBasicPlugin(gap func() []string) *basicPlugin {
	return &basicPlugin{
		Name:         "Main",
		Helpable:     true,
		getAllPlugin: gap,
	}
}

func (bh *basicPlugin) GetName() string {
	return bh.Name
}

func (bh *basicPlugin) RegisterHandler(d *ext.Dispatcher) {
	d.AddHandler(handlers.NewCommand("start", bh.cmdStart))
	d.AddHandler(handlers.NewCommand("ping", bh.cmdPing))
	d.AddHandler(handlers.NewCommand("privacy", bh.cmdPrivacy))
	d.AddHandler(handlers.NewCommand("donate", bh.cmdDonate))
	d.AddHandler(handlers.NewCommand("help", bh.cmdHelp))
	d.AddHandler(handlers.NewCallback(callbackquery.Prefix("help:"), bh.cqHelp))
}
