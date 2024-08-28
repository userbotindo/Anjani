package main

import (
	"context"
	"flag"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/jackc/pgx/v5/stdlib"
	"github.com/pressly/goose/v3"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/common/config"
)

func main() {
	cfg := config.GetConfig()

	ctx := context.Background()
	upFlag := flag.Bool("up", false, "Perform migration up")
	downFlag := flag.Bool("down", false, "Perform migration down")
	flag.Parse()

	if err := goose.SetDialect("postgres"); err != nil {
		log.Fatal().Err(err).Msg("failed to setup database driver")
	}

	dbConfig, err := pgxpool.ParseConfig(cfg.Database.GetUri())
	if err != nil {
		log.Fatal().Err(err).Msg("failed to parse database uri")
	}

	db, err := pgxpool.NewWithConfig(ctx, dbConfig)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to connect to database")
	}
	dbConn := stdlib.OpenDBFromPool(db)

	if *upFlag {
		if err := goose.Up(dbConn, "db/migrations/"); err != nil {
			fmt.Println(err)
			log.Fatal().Err(err).Msg("failed to run migrations")
		}
	} else if *downFlag {
		if err := goose.Down(dbConn, "db/migrations/"); err != nil {
			log.Fatal().Err(err).Msg("failed to downgrade migrations")
		}
	} else {
		log.Fatal().Msg("please specify -up or -down")
	}
}
