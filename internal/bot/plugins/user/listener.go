package user

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/userbotindo/anjani/internal/common/util"
)

func (up *userPlugin) onMessage(b *gotgbot.Bot, ctx *ext.Context) error {
	c := ctx.EffectiveChat
	u := ctx.EffectiveUser

	if c == nil || u == nil { // Ignore service messages
		return nil
	}

	uData, err := up.getUser(u.Id)
	if err != nil {
		return err
	}

	if c.Type == "private" {
		_, err := up.upsertUser(b, u.Id, u.Username, util.BoolPtr(true))
		return err
		// TODO: handle forwared messages
	}

	up.upsertChat(b, c.Id, c.Title, c.Type, c.IsForum, util.BoolPtr(true))
	up.upsertUser(b, u.Id, u.Username, util.BoolPtr(uData != nil && *uData.IsStarted))
	// TODO: handle forwarded messages
	return nil
}
