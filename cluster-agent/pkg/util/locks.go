package util

// HasKubeliteLock returns true if this MicroK8s deployment is running Kubelite.
func HasKubeliteLock() bool {
	return FileExists(SnapDataPath("var", "lock", "lite.lock"))
}

// HasDqliteLock returns true if this MicroK8s deployment is running Dqlite.
func HasDqliteLock() bool {
	return FileExists(SnapDataPath("var", "lock", "ha-cluster"))
}
