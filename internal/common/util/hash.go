package util

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"strconv"
)

func HashMd5(id interface{}, salt string) (string, error) {
	var idStr string
	switch v := id.(type) {
	case int:
		idStr = strconv.Itoa(v)
	case int64:
		idStr = strconv.Itoa(int(v))
	case string:
		idStr = v
	default:
		return "", fmt.Errorf("unsupported id type: %T", id)
	}

	hash := md5.Sum([]byte(idStr + salt))
	return hex.EncodeToString(hash[:]), nil
}
