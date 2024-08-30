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

func (h *basicPlugin) cmdPrivacy(b *gotgbot.Bot, ctx *ext.Context) error {
	ctx.EffectiveMessage.Reply(b, "You can find our privacy policy below.", &gotgbot.SendMessageOpts{
		ReplyMarkup: gotgbot.InlineKeyboardMarkup{
			InlineKeyboard: [][]gotgbot.InlineKeyboardButton{{
				{Text: "Privacy Policy", Url: "https://userbotindo.com/privacy"},
			}},
		},
	})
	return nil
}

func (h *basicPlugin) cmdStart(_ *gotgbot.Bot, _ *ext.Context) error {
	return nil
}

func (h *basicPlugin) cmdDonate(b *gotgbot.Bot, ctx *ext.Context) error {
	ctx.EffectiveMessage.Reply(b, `Hi, glad to see you want to donate!
You can donate to us on [our site](https://userbotindo.com/donate?ref=anjani).
Our team is fully handled by volunteers,, and every little helps to improve our services.
Thank you for your support!`, &gotgbot.SendMessageOpts{
		ParseMode: "markdown",
		LinkPreviewOptions: &gotgbot.LinkPreviewOptions{
			IsDisabled: true,
		},
	})
	return nil
}
