package config

import (
	"os"
	"strconv"
	"sync"

	"github.com/joho/godotenv"
	"github.com/rs/zerolog/log"
)

func (c *Config) loadEnv() error {
	cwd, _ := os.Getwd()

	err := godotenv.Load(cwd + "/.env")
	if err != nil {
		log.Info().Msg(".env file not found, will use os env instead")
	}

	c.Telegram.BotToken = os.Getenv("BOT_TOKEN")
	if c.Telegram.BotToken == "" {
		log.Fatal().Msg("BOT_TOKEN must be set")
	}

	var ownerId = 0
	var envOwnerId = os.Getenv("OWNER_ID")
	if envOwnerId != "" {
		ownerId, err = strconv.Atoi(envOwnerId)
		if err != nil {
			log.Fatal().Msg("OWNER_ID must be a valid integer")
			return err
		}
	}
	c.Telegram.OwnerId = ownerId
	c.Telegram.LogChannel = os.Getenv("LOG_CHANNEL")

	if logChannel := os.Getenv("LOG_CHANNEL"); logChannel != "" {
		c.Telegram.LogChannel = logChannel
	}
	c.Telegram.AlertChannel = os.Getenv("ALERT_CHANNEL")
	c.Telegram.LoginUrl = os.Getenv("LOGIN_URL")

	c.Plugin.FeatureFlag = os.Getenv("FEATURE_FLAG")
	c.Plugin.PluginFlag = os.Getenv("PLUGIN_FLAG")

	c.Database.Host = os.Getenv("DB_HOST")
	c.Database.Port = os.Getenv("DB_PORT")
	c.Database.User = os.Getenv("DB_USER")
	c.Database.Password = os.Getenv("DB_PASSWORD")
	c.Database.Database = os.Getenv("DB_NAME")

	c.SpamDetection.ApiKey = os.Getenv("SPAM_DETECTION_API_KEY")
	c.SpamDetection.ApiUrl = os.Getenv("SPAM_DETECTION_API_URL")
	c.ThirdParty.SpamWatchApiKey = os.Getenv("SPAM_WATCH_API_KEY")

	c.Extras.LogLevel = os.Getenv("LOG_LEVEL")
	return nil
}

var (
	cfg  Config
	once sync.Once
)

func GetConfig() Config {
	once.Do(func() {
		err := cfg.loadEnv()
		if err != nil {
			log.Fatal().Err(err).Msg("failed to load env")
		}
	})
	return cfg
}
