package util_test

import (
	"context"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
)

func TestUpdateDqliteIP(t *testing.T) {
	// Create test data
	for file, contents := range map[string]string{
		"testdata/var/kubernetes/backend/info.yaml": `
Address: 127.0.0.1:19001
ID: 1236189235178654365
Role: 0
`,
		"testdata/var/kubernetes/backend/cluster.yaml": `
- Address: 127.0.0.1:19001
  ID: 1236189235178654365
  Role: 0
`,
	} {
		if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
			t.Fatalf("Failed to create test directory: %s", err)
		}
		if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
			t.Fatalf("Failed to create test file: %s", err)
		}
	}
	defer os.RemoveAll("testdata/var")

	m := &utiltest.MockRunner{}
	utiltest.WithMockRunner(m, func(t *testing.T) {
		if err := util.UpdateDqliteIP(context.Background(), "10.10.10.10"); err != nil {
			t.Fatalf("Failed to update dqlite: %q", err)
		}

		expectedCommands := []string{
			"snapctl restart microk8s.daemon-k8s-dqlite",
			"snapctl restart microk8s.daemon-apiserver",
		}

		if !reflect.DeepEqual(expectedCommands, m.CalledWithCommand) {
			t.Fatalf("Expected commands %#v but %#v was executed instead", expectedCommands, m.CalledWithCommand)
		}

		s, err := util.ReadFile("testdata/var/kubernetes/backend/update.yaml")
		if err != nil {
			t.Fatalf("Expected update.yaml file to be created, but it is not: %q", err)
		}
		if strings.TrimSpace(s) != "Address: 10.10.10.10:19001" {
			t.Fatalf("Expected update.yaml file to contain new address, but it contains %q", s)
		}
	})(t)
}

func TestWaitForDqliteCluster(t *testing.T) {
	t.Run("Cancel", func(t *testing.T) {
		ctx, cancel := context.WithCancel(context.Background())
		cancel()

		_, err := util.WaitForDqliteCluster(ctx, func(util.DqliteCluster) (bool, error) { return true, nil })
		if err == nil {
			t.Fatalf("Expected an error but did not receive any")
		}
	})

	t.Run("OK", func(t *testing.T) {
		// Create test data
		for file, contents := range map[string]string{
			"testdata/var/kubernetes/backend/info.yaml": `
Address: 127.0.0.1:19001
ID: 1236189235178654365
Role: 0
`,
			"testdata/var/kubernetes/backend/cluster.yaml": `
- Address: 127.0.0.1:19001
  ID: 1236189235178654365
  Role: 0
`,
		} {
			if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
				t.Fatalf("Failed to create test directory: %s", err)
			}
			if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
				t.Fatalf("Failed to create test file: %s", err)
			}
		}
		defer os.RemoveAll("testdata/var")

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)

		go func() {
			<-time.After(time.Second)
			if err := os.WriteFile("testdata/var/kubernetes/backend/cluster.yaml", []byte(`
- Address: 10.10.10.10:19001
  ID: 1236189235178654365
  Role: 0
`), 0660); err != nil {
				cancel()
			}
		}()

		cluster, err := util.WaitForDqliteCluster(ctx, func(cluster util.DqliteCluster) (bool, error) {
			return len(cluster) == 1 && cluster[0].Address == "10.10.10.10:19001", nil
		})
		if err != nil {
			t.Fatalf("Expected no errors but received: %q", err)
		}
		if cluster[0].Address != "10.10.10.10:19001" {
			t.Fatalf("Expected cluster to contain update node information, but received %#v", cluster)
		}
	})
}
