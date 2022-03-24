package v1_test

import (
	"encoding/json"
	"testing"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
)

func TestUnmarshalRestartServiceField(t *testing.T) {
	for _, tc := range []struct {
		b             string
		expectedValue v1.RestartServiceField
	}{
		{b: "true", expectedValue: true},
		{b: "false", expectedValue: false},
		{b: "null", expectedValue: false},
		{b: `"yes"`, expectedValue: true},
	} {
		t.Run(tc.b, func(t *testing.T) {
			var v v1.RestartServiceField
			if err := json.Unmarshal([]byte(tc.b), &v); err != nil {
				t.Fatalf("Expected no error but received %q", err)
			}
			if v != tc.expectedValue {
				t.Fatalf("Expected value to be %v, but it was %v", tc.expectedValue, v)
			}
		})
	}
}
