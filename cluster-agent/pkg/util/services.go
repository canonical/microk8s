package util

import (
	"context"
	"fmt"
	"strings"
)

// Restart a MicroK8s service, handling the case where the MicroK8s cluster is running Kubelite.
func Restart(ctx context.Context, serviceName string) error {
	if HasKubeliteLock() {
		switch serviceName {
		case "apiserver", "proxy", "kubelet", "scheduler", "controller-manager":
			serviceName = "kubelite"
		}
	}
	return RunCommand(ctx, []string{"snapctl", "restart", fmt.Sprintf("microk8s.daemon-%s", serviceName)})
}

// GetServiceArgument retrieves the value of a specific argument from the $SNAP_DATA/args/$service file.
// The argument name should include preceeding dashes (e.g. "--secure-port").
// If any errors occur, or the argument is not present, an empty string is returned.
func GetServiceArgument(serviceName string, argument string) string {
	arguments, err := ReadFile(SnapDataPath("args", serviceName))
	if err != nil {
		return ""
	}

	for _, line := range strings.Split(arguments, "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, argument) {
			continue
		}
		// parse "--argument value" and "--argument=value" variants
		line = line[strings.LastIndex(line, " ")+1:]
		line = line[strings.LastIndex(line, "=")+1:]
		return line
	}
	return ""
}
