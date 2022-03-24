package util

import (
	"reflect"
	"testing"
)

func TestParseControlPlaneNodeIPs(t *testing.T) {
	b := []byte(`{
		"items": [
			{"status": {"addresses": [{"type": "InternalIP", "address": "10.0.0.1"}, {"type": "Hostname", "address": "node1"}]}},
			{"status": {"addresses": [{"type": "InternalIP", "address": "10.0.0.2"}, {"type": "Hostname", "address": "node2"}]}}
		]
	}`)
	expectedIPs := []string{"10.0.0.1", "10.0.0.2"}

	nodes, err := parseControlPlaneNodeIPs(b)
	if err != nil {
		t.Fatalf("expected no error but got %q", err)
	}
	if !reflect.DeepEqual(nodes, expectedIPs) {
		t.Fatalf("expected list of nodes to be %v but it was %v instead", expectedIPs, nodes)
	}
}
