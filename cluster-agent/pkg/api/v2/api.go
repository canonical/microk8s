package v2

// API implements the v2 API.
type API struct {
	// ListControlPlaneNodeIPs is used in v2/join to list the IP addresses of the
	// known control plane nodes.
	ListControlPlaneNodeIPs ListControlPlaneNodeIPsFunc
}
