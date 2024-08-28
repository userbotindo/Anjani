package plugins

import (
	"time"

	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/PaulSonOfLars/gotgbot/v2/ext/handlers"
	"github.com/rs/zerolog/log"
)

var BasicPlugin = &Plugin{
	Name:     "Basic",
	Helpable: true,
}

func cmdPing(b *gotgbot.Bot, ctx *ext.Context) error {
	start := time.Now()
	msg, err := ctx.EffectiveMessage.Reply(b, "Pong!", nil)
	if err != nil {
		return err
	}
	elapsed := time.Since(start)
	msg.EditText(b, "Pong! "+elapsed.String(), nil)
	return nil
}

func LoadPlugin(d *ext.Dispatcher) {
	log.Info().Msg("Loading Basic plugin")
	d.AddHandler(handlers.NewCommand("ping", cmdPing))
}
