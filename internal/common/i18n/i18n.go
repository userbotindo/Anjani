package i18n

import (
	"embed"
	"fmt"
	"io/fs"
)

const (
	localePath  = "locale"
	defaultLang = "en"
)

var LocaleMap = make(map[string][]byte)

func LoadLocale() {
	// read all .yaml files in locale directory
	// and store it in LocaleMap
	localeFiles, err := fs.ReadDir(embed.FS{}, localePath)
	if err != nil {
		fmt.Println(err)
	}

	fmt.Println(localeFiles)

}

func GetString(langCode, key string) string {
	if _, ok := LocaleMap[langCode]; !ok {
		langCode = defaultLang
	}

	return string(LocaleMap[langCode])
}
