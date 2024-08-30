package basic

import (
	"time"

	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
)

func (h *basicPlugin) cmdPing(b *gotgbot.Bot, ctx *ext.Context) error {
	start := time.Now()
	msg, err := ctx.EffectiveMessage.Reply(b, "Pong!", nil)
	if err != nil {
		return err
	}
	elapsed := time.Since(start)
	msg.EditText(b, "Pong! "+elapsed.String(), nil)
	return nil
}
