package basic

import (
	"fmt"
	"strings"
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

func (h *basicPlugin) cmdStart(b *gotgbot.Bot, ctx *ext.Context) error {
	permission := []string{
		"change_info",
		"post_messages",
		"edit_messages",
		"delete_messages",
		"restrict_members",
		"invite_users",
		"pin_messages",
		"promote_members",
		"manage_video_chats",
		"manage_chat",
	}

	ctx.EffectiveMessage.Reply(b, `Hey there! my name is **Anjani**.
Any questions on how to use me? use /help
Join Our [Group](https://t.me/userbotindo) If You wanna Report Issue 🙂
I'm here to make your group management fun and easy!
**Managed With ❤️ By :** [UserbotIndo Team](https://t.me/userbotindo)
Wanna Add me to your Group? Just click the button below!`, &gotgbot.SendMessageOpts{
		ParseMode: "markdown",
		LinkPreviewOptions: &gotgbot.LinkPreviewOptions{
			IsDisabled: true,
		},
		ReplyMarkup: gotgbot.InlineKeyboardMarkup{
			InlineKeyboard: [][]gotgbot.InlineKeyboardButton{{
				{Text: "Add to Group", Url: "t.me/dAnjani_bot?startgroup=true&admin=" + strings.Join(permission, "+")},
				{Text: "Help", Url: "t.me/dAnjani_bot?start=help"},
			}, {
				{Text: "Status", Url: "https://status.userbotindo.com"},
				{Text: "Donate", Url: "https://userbotindo.com/donate?ref=anjani"},
			}},
		},
	})
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

func (h *basicPlugin) cmdHelp(b *gotgbot.Bot, ctx *ext.Context) error {
	chat := ctx.EffectiveChat

	if chat.Type != "private" {
		ctx.EffectiveMessage.Reply(b, "Contact me in PM to get the list of possible commands.", &gotgbot.SendMessageOpts{
			ReplyMarkup: gotgbot.InlineKeyboardMarkup{
				InlineKeyboard: [][]gotgbot.InlineKeyboardButton{{
					{Text: "Help", Url: "t.me/dAnjani_bot?start=help"},
				}},
			},
		})
		return nil
	}

	var p []gotgbot.InlineKeyboardButton

	for _, cmd := range h.getAllPlugin() {
		p = append(p, gotgbot.InlineKeyboardButton{Text: cmd, CallbackData: fmt.Sprintf("help:%s", cmd)})
	}

	ctx.EffectiveMessage.Reply(b, "Here is the list of available commands", &gotgbot.SendMessageOpts{
		ReplyMarkup: gotgbot.InlineKeyboardMarkup{
			InlineKeyboard: [][]gotgbot.InlineKeyboardButton{p},
		},
	})

	return nil
}

func (h *basicPlugin) cqHelp(b *gotgbot.Bot, ctx *ext.Context) error {
	cb := ctx.Update.CallbackQuery

	pn := strings.Split(cb.Data, ":")[1]
	cb.Answer(b, &gotgbot.AnswerCallbackQueryOpts{
		Text: fmt.Sprintf("%s clicked", pn),
	})
	return nil
}
