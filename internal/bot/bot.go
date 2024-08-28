package bot

import (
	"github.com/PaulSonOfLars/gotgbot/v2"
	"github.com/PaulSonOfLars/gotgbot/v2/ext"
	"github.com/userbotindo/anjani/internal/bot/handler"
	"github.com/userbotindo/anjani/internal/common/config"
)

func Run(cfg *config.Config, bot *gotgbot.Bot) *ext.Updater {
	return handler.CreateDispatcher(bot)
}
