package util

import (
	"fmt"
	"os"
	"os/user"
	"strconv"
)

// FileExists returns true if the specified path exists.
func FileExists(path string) bool {
	_, err := os.Stat(path)
	return !os.IsNotExist(err)
}

// SetupPermissions attempts to set file permissions to 0660 and group to `microk8s` for a given file.
// SetupPermissions will knowingly ignore any errors, as failing to update permissions will only occur
// in extraordinary situations, and will never break the MicroK8s cluster.
func SetupPermissions(path string) {
	os.Chmod(path, 0660)
	if group, err := user.LookupGroup("microk8s"); err == nil {
		if gid, err := strconv.ParseInt(group.Gid, 10, 32); err == nil {
			os.Chown(path, -1, int(gid))
		}
	}
}

// ReadFile returns the file contents as a string.
func ReadFile(path string) (string, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("failed to read %s: %w", path, err)
	}
	return string(b), nil
}
