package main

import (
	"os"
	"os/signal"
	"syscall"

	"github.com/jackc/pgx/v5/stdlib"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/bot"
	"github.com/userbotindo/anjani/internal/common/config"
	"github.com/userbotindo/anjani/internal/common/logger"
	"github.com/userbotindo/anjani/internal/common/storage"
)

//go:generate sqlc generate -f ../../sqlc.yml

func main() {
	cfg := config.GetConfig()

	err := logger.InitLogger(cfg.Extras.LogLevel, logger.LogFormatLogFmt)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to initialize logger")
	}

	b := CreateBot(&cfg)

	pg := storage.New(cfg.Database)
	storage.Migrate(stdlib.OpenDBFromPool(pg), "up")
	defer pg.Close()

	sig := make(chan os.Signal, 1)
	done := make(chan bool, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM, syscall.SIGABRT)
	go func() {
		<-sig
		done <- true
	}()

	up := bot.Run(&cfg, b, pg)
	defer up.Stop()

	<-done
	log.Info().Msg("Shutting down")
}
