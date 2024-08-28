package main

import (
	"fmt"

	"github.com/userbotindo/anjani/internal/common/config"
)

func main() {
	cfg := config.GetConfig()
	fmt.Printf("%+v\n", cfg.Database)
}
