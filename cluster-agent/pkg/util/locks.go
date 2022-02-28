package util

import "os"

// HasKubeliteLock returns true if this MicroK8s deployment is running Kubelite.
func HasKubeliteLock() bool {
	return FileExists(SnapDataPath("var", "lock", "lite.lock"))
}

// HasDqliteLock returns true if this MicroK8s deployment is running Dqlite.
func HasDqliteLock() bool {
	return FileExists(SnapDataPath("var", "lock", "ha-cluster"))
}

// CreateNoCertsReissueLock creates a lock file that disables re-issuing the certificates
// on this MicroK8s node (to avoid breaking the cluster).
func CreateNoCertsReissueLock() error {
	_, err := os.OpenFile(SnapDataPath("var", "lock", "no-cert-reissue"), os.O_CREATE, 0600)
	return err
}

// HasNoCertsReissueLock returns true if re-issuing certificates is disabled on this MicroK8s deployment.
func HasNoCertsReissueLock() bool {
	return FileExists(SnapDataPath("var", "lock", "no-cert-reissue"))
}
