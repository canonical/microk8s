package util_test

import (
	"context"
	"os"
	"reflect"
	"strings"
	"testing"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
)

func TestCalico(t *testing.T) {
	m := &utiltest.MockRunner{}
	utiltest.WithMockRunner(m, func(t *testing.T) {
		// Setup
		if err := os.MkdirAll("testdata/args/cni-network", 0755); err != nil {
			t.Fatalf("Failed to create test directory: %q", err)
		}
		initialContents := `some contents here and there. value: "first-found"`
		if err := os.WriteFile("testdata/args/cni-network/cni.yaml", []byte(initialContents), 0660); err != nil {
			t.Fatalf("Failed to create test cni.yaml: %q", err)
		}
		defer os.RemoveAll("testdata/args")

		if err := util.MaybePatchCalicoAutoDetectionMethod(context.Background(), "10.10.10.10", true); err != nil {
			t.Fatalf("Expected no errors but received %q", err)
		}
		s, err := util.ReadFile("testdata/args/cni-network/cni.yaml")
		if err != nil {
			t.Fatalf("Expected no errors reading cni.yaml but received %q", err)
		}
		if !strings.Contains(s, `"can-reach=10.10.10.10"`) {
			t.Fatalf("Expected cni.yaml to contain %q but it does not", `"can-reach=10.10.10.10"`)
		}

		expectedCommands := []string{
			"testdata/microk8s-kubectl.wrapper apply -f testdata/args/cni-network/cni.yaml",
		}

		if !reflect.DeepEqual(expectedCommands, m.CalledWithCommand) {
			t.Fatalf("Expected commands %#v but %#v was executed instead", expectedCommands, m.CalledWithCommand)
		}
	})(t)
}
