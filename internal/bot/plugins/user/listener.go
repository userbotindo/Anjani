package user

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
)

func (up *userPlugin) onMessage(b *gotgbot.Bot, ctx *ext.Context) error {
	var hasStarted bool
	if ctx.EffectiveChat.Type == "private" {
		hasStarted = true
	}

	_, err := up.upsertUser(b, ctx.EffectiveUser.Id, ctx.EffectiveUser.Username, &hasStarted)
	if err != nil {
		return err
	}
	return nil
}
