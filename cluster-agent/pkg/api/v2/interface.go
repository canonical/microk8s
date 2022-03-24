package v2

import "context"

// ListControlPlaneNodeIPsFunc returns a list of the known control plane nodes of a MicroK8s cluster.
type ListControlPlaneNodeIPsFunc func(ctx context.Context) ([]string, error)
