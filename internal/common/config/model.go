package config

type Config struct {
	Telegram      TelegramConfig
	Plugin        PluginConfig
	Database      DatabaseConfig
	SpamDetection SpamDetectionConfig
	ThirdParty    ThirdPartyConfig
	Extras        ExtrasConfig
}

type TelegramConfig struct {
	BotToken     string
	OwnerId      int
	LogChannel   string
	AlertChannel string
	LoginUrl     string
}

type PluginConfig struct {
	PluginFlag  string
	FeatureFlag string
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Database string
}

func (d *DatabaseConfig) GetUri() string {
	return "postgresql://" + d.User + ":" + d.Password + "@" + d.Host + ":" + d.Port + "/" + d.Database
}

type SpamDetectionConfig struct {
	ApiKey string
	ApiUrl string
}

type ThirdPartyConfig struct {
	SpamWatchApiKey string
}

type ExtrasConfig struct {
	LogLevel string
}
