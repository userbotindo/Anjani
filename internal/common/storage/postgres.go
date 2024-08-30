package storage

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/pressly/goose/v3"
	"github.com/rs/zerolog/log"
	"github.com/userbotindo/anjani/internal/common/config"
)

const uriFormat = "postgresql://%s:%s@%s:%s/%s"

func Migrate(db *sql.DB, command string) {
	log.Info().Msg(fmt.Sprintf("Running %s migrations", command))
	if err := goose.RunContext(context.Background(), command, db, "db/migrations/"); err != nil {
		log.Fatal().Err(err).Msg("failed to run migrations")
	}
}

func generateUri(cfg config.DatabaseConfig) string {
	uri := fmt.Sprintf(uriFormat, cfg.User, cfg.Password, cfg.Host, cfg.Port, cfg.Database)

	return uri
}

func connect(cfg config.DatabaseConfig) *pgxpool.Pool {
	uri := generateUri(cfg)
	dbConfig, err := pgxpool.ParseConfig(uri)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to parse database uri")
	}

	log.Debug().Msg("creating database connection pool")
	db, err := pgxpool.NewWithConfig(context.Background(), dbConfig)
	if err != nil {
		log.Fatal().Err(err).Msg("failed to create database connection pool")
	}

	log.Debug().Msg("Connecting to database")
	if err := db.Ping(context.Background()); err != nil {
		log.Fatal().Err(err).Msg("failed to ping database")
	}
	log.Info().Msg("Connected to database")

	return db
}

func New(cfg config.DatabaseConfig) *pgxpool.Pool {
	return connect(cfg)
}
