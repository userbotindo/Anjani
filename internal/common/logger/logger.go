package logger

import (
	"io"
	"os"
	"time"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/rs/zerolog/pkgerrors"
)

const (
	LogFormatLogFmt = "LOGFMT"
	LogFormatJSON   = "JSON"
)

const (
	LogLevelTrace = "TRACE"
	LogLevelDebug = "DEBUG"
	LogLevelWarn  = "WARN"
)

func InitLogger(level string, format string) error {
	zerolog.TimeFieldFormat = time.RFC3339
	zerolog.ErrorStackMarshaler = pkgerrors.MarshalStack

	if level == "TRACE" {
		zerolog.SetGlobalLevel(zerolog.TraceLevel)
	} else if level == "DEBUG" {
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	} else if level == "WARN" {
		zerolog.SetGlobalLevel(zerolog.WarnLevel)
	} else {
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	}

	writers := []io.Writer{}
	if format == LogFormatLogFmt {
		writers = append(writers, zerolog.ConsoleWriter{Out: os.Stdout})
	}

	zlogWriter := zerolog.MultiLevelWriter(writers...)

	log.Logger = zerolog.New(zlogWriter).With().Stack().Timestamp().Logger()
	return nil
}
