package util

import (
	"os"
	"path/filepath"
)

var (
	// SnapData is the $SNAP_DATA directory.
	SnapData string
)

func init() {
	SnapData = os.Getenv("SNAP_DATA")
}

// SnapDataPath returns the path for a file under $SNAP_DATA.
func SnapDataPath(elements ...string) string {
	return filepath.Join(append([]string{SnapData}, elements...)...)
}
