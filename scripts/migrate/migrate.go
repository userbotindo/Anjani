package main

import (
	"flag"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/common/config"
	"github.com/userbotindo/anjani/internal/common/logger"
	"github.com/userbotindo/anjani/internal/common/storage"
)

func main() {
	cfg := config.GetConfig()
	err := logger.InitLogger(cfg.Extras.LogLevel, logger.LogFormatLogFmt)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to initialize logger")
	}

	isUp := flag.Bool("up", false, "Migrate up")
	isDown := flag.Bool("down", false, "Migrate down")
	flag.Parse()

	db := storage.New(cfg.Database)
	dbConn := stdlib.OpenDBFromPool(db)

	if *isUp {
		storage.Migrate(dbConn, "up")
	} else if *isDown {
		storage.Migrate(dbConn, "down")
	} else {
		log.Fatal().Msg("please specify -up or -down")
	}
}
