package util

import "net"

// GetRemoteHost returns the hostname that should be used for communicating with the joining node.
// The endpoint is either the hostname (if it can be resolved), or the remote IP address, as read from the HTTP request.
func GetRemoteHost(hostname string, remoteAddress string) string {
	if ips, err := net.LookupIP(hostname); err == nil && len(ips) > 0 {
		return hostname
	}
	host, _, _ := net.SplitHostPort(remoteAddress)
	return host
}
