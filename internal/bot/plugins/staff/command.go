package staff

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
)

func (h *staffPlugin) cmdDebug(b *gotgbot.Bot, ctx *ext.Context) error {
	ctx.EffectiveMessage.Chat.SendMessage(b, "hello world", nil)
	return nil
}
