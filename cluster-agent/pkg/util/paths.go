package util

import (
	"os"
	"path/filepath"
)

var (
	// Snap is the $SNAP directory.
	Snap string
	// SnapData is the $SNAP_DATA directory.
	SnapData string
)

func init() {
	Snap = os.Getenv("SNAP")
	SnapData = os.Getenv("SNAP_DATA")
}

// SnapDataPath returns the path for a file under $SNAP_DATA.
func SnapDataPath(elements ...string) string {
	return filepath.Join(append([]string{SnapData}, elements...)...)
}

// SnapPath returns the path for a file under $SNAP.
func SnapPath(elements ...string) string {
	return filepath.Join(append([]string{Snap}, elements...)...)
}
