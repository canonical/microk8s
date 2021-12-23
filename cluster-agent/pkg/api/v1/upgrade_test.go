package v1_test

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
)

func TestUpgrade(t *testing.T) {
	for file, contents := range map[string]string{
		"testdata/credentials/callback-token.txt":                      "valid-token",
		"testdata/upgrade-scripts/001-custom-upgrade/prepare-node.sh":  "",
		"testdata/upgrade-scripts/001-custom-upgrade/commit-node.sh":   "",
		"testdata/upgrade-scripts/001-custom-upgrade/rollback-node.sh": "",
	} {
		if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
			t.Fatalf("Failed to create test directory: %s", err)
		}
		if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
			t.Fatalf("Failed to create test file: %s", err)
		}
	}
	defer os.RemoveAll("testdata/credentials")
	defer os.RemoveAll("testdata/upgrade-scripts")

	t.Run("Invalid", func(t *testing.T) {
		for _, tc := range []struct {
			name string
			req  v1.UpgradeRequest
		}{
			{name: "invalid-token", req: v1.UpgradeRequest{CallbackToken: "invalid-token"}},
			{name: "unknown-phase", req: v1.UpgradeRequest{CallbackToken: "valid-token", UpgradePhase: "invalid-phase"}},
			{name: "invalid-upgrade", req: v1.UpgradeRequest{CallbackToken: "valid-token", UpgradePhase: "prepare", UpgradeName: "999-invalid-upgrade"}},
		} {
			m := &utiltest.MockRunner{}
			utiltest.WithMockRunner(m, func(t *testing.T) {
				t.Run(tc.name, func(t *testing.T) {
					err := v1.Upgrade(context.Background(), tc.req)
					if err == nil {
						t.Fatal("Expected an error but did not receive any")
					}
					if len(m.CalledWithCommand) > 0 {
						t.Fatalf("Expected no commands to be called, but received %#v", m.CalledWithCommand)
					}
				})
			})(t)
		}
	})

	t.Run("Success", func(t *testing.T) {
		for _, phase := range []string{"prepare", "commit", "rollback"} {
			m := &utiltest.MockRunner{}
			utiltest.WithMockRunner(m, func(t *testing.T) {
				t.Run(phase, func(t *testing.T) {
					err := v1.Upgrade(context.Background(), v1.UpgradeRequest{
						CallbackToken: "valid-token",
						UpgradeName:   "001-custom-upgrade",
						UpgradePhase:  phase,
					})
					if err != nil {
						t.Fatalf("Expected no errors but received %q", err)
					}
					expectedCommand := fmt.Sprintf("testdata/upgrade-scripts/001-custom-upgrade/%s-node.sh", phase)
					if len(m.CalledWithCommand) != 1 || m.CalledWithCommand[0] != expectedCommand {
						t.Fatalf("Expected command %q, but received %#v", expectedCommand, m.CalledWithCommand)
					}
				})
			})(t)
		}
	})
}
