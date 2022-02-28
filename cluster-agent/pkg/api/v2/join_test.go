package v2_test

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	v2 "github.com/canonical/microk8s/cluster-agent/pkg/api/v2"
	"github.com/canonical/microk8s/cluster-agent/pkg/util"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
)

// TestJoin tests responses when joining control plane and worker nodes in an existing cluster.
func TestJoin(t *testing.T) {
	// Create test data
	for file, contents := range map[string]string{
		"testdata/var/lock/ha-cluster":                "",
		"testdata/var/kubernetes/backend/cluster.crt": "DQLITE CERTIFICATE DATA",
		"testdata/var/kubernetes/backend/cluster.key": "DQLITE KEY DATA",
		"testdata/var/kubernetes/backend/info.yaml": `
Address: 10.10.10.10:19001
ID: 1238719276943521
Role: 0
`,
		"testdata/var/kubernetes/backend/cluster.yaml": `
- Address: 10.10.10.10:19001
  ID: 1238719276943521
  Role: 0
- Address: 10.10.10.11:19001
  ID: 12312648746587658
  Role: 0
- Address: 10.10.10.100:19001
  ID: 12312648746587655
  Role: 2
`,
		"testdata/certs/ca.crt":                    "CA CERTIFICATE DATA",
		"testdata/certs/ca.key":                    "CA KEY DATA",
		"testdata/certs/serviceaccount.key":        "SERVICE ACCOUNT KEY DATA",
		"testdata/args/kubelet":                    "kubelet arguments\n",
		"testdata/args/kube-apiserver":             "--secure-port 16443",
		"testdata/args/cni-network/cni.yaml":       `some random content. "first-found"`,
		"testdata/args/cluster-agent":              "--bind=0.0.0.0:25000",
		"testdata/credentials/cluster-tokens.txt":  "worker-token\ncontrol-plane-token",
		"testdata/credentials/callback-tokens.txt": "",
		"testdata/credentials/callback-token.txt":  "callback-token",
		"testdata/credentials/known_tokens.csv": `kube-proxy-token,system:kube-proxy,kube-proxy,
admin-token-123,admin,admin,"system:masters"
`,
	} {
		if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
			t.Fatalf("Failed to create test directory: %s", err)
		}
		if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
			t.Fatalf("Failed to create test file: %s", err)
		}
		defer os.RemoveAll(filepath.Dir(file))
	}
	defer os.RemoveAll("testdata/var")

	t.Run("InvalidToken", func(t *testing.T) {
		resp, err := v2.Join(context.Background(), v2.JoinRequest{ClusterToken: "invalid-token"})
		if err == nil {
			t.Fatalf("Expected error but did not receive any")
		}
		if resp != nil {
			t.Fatalf("Expected a nil response but received %#v", resp)
		}
	})

	t.Run("ControlPlane", func(t *testing.T) {
		m := &utiltest.MockRunner{}
		utiltest.WithMockRunner(m, func(t *testing.T) {

			resp, err := v2.Join(context.Background(), v2.JoinRequest{
				ClusterToken:     "control-plane-token",
				RemoteHostName:   "some-invalid-hostname",
				ClusterAgentPort: "25000",
				HostPort:         "10.10.10.10:25000",
				RemoteAddress:    "10.10.10.13:41532",
				WorkerOnly:       false,
			})
			if err != nil {
				t.Fatalf("Expected no errors, but received %q", err)
			}
			if resp == nil {
				t.Fatal("Expected a response but received nil instead")
			}

			expectedResponse := &v2.JoinResponse{
				CertificateAuthority:     "CA CERTIFICATE DATA",
				CallbackToken:            "callback-token",
				APIServerPort:            "16443",
				KubeletArgs:              "kubelet arguments\n\n--hostname-override=10.10.10.13",
				HostNameOverride:         "10.10.10.13",
				DqliteVoterNodes:         []string{"10.10.10.10:19001", "10.10.10.11:19001"},
				ServiceAccountKey:        "SERVICE ACCOUNT KEY DATA",
				CertificateAuthorityKey:  func(s string) *string { return &s }("CA KEY DATA"),
				AdminToken:               "admin-token-123",
				DqliteClusterCertificate: "DQLITE CERTIFICATE DATA",
				DqliteClusterKey:         "DQLITE KEY DATA",
			}
			if !reflect.DeepEqual(*resp, *expectedResponse) {
				t.Fatalf("Expected response %#v, but received %#v instead", expectedResponse, resp)
			}
			if util.IsValidClusterToken("control-plane-token") {
				t.Fatalf("Expected control-plane-token to not be a valid cluster token after being used, but it is")
			}

			expectedCommands := []string{
				"testdata/microk8s-kubectl.wrapper apply -f testdata/args/cni-network/cni.yaml",
			}
			if !reflect.DeepEqual(expectedCommands, m.CalledWithCommand) {
				t.Fatalf("Expected commands %#v, but %#v was executed", expectedCommands, m.CalledWithCommand)
			}
			if !util.HasNoCertsReissueLock() {
				t.Fatal("Expected certificate reissue lock to be in place after successful join, but it is not")
			}
		})(t)
	})

	t.Run("Worker", func(t *testing.T) {
		m := &utiltest.MockRunner{}
		utiltest.WithMockRunner(m, func(t *testing.T) {
			resp, err := v2.Join(context.Background(), v2.JoinRequest{
				ClusterToken:     "worker-token",
				RemoteHostName:   "10.10.10.12",
				RemoteAddress:    "10.10.10.12:31451",
				WorkerOnly:       true,
				HostPort:         "10.10.10.10:25000",
				ClusterAgentPort: "25000",
			})
			if err != nil {
				t.Fatalf("Expected no errors, but received %q", err)
			}
			if resp == nil {
				t.Fatal("Expected a response but received nil instead")
			}
			expectedResponse := &v2.JoinResponse{
				CertificateAuthority: "CA CERTIFICATE DATA",
				CallbackToken:        "callback-token",
				APIServerPort:        "16443",
				KubeletArgs:          "kubelet arguments\n",
				HostNameOverride:     "10.10.10.12",
				ControlPlaneNodes:    []string{},
			}

			if !reflect.DeepEqual(*resp, *expectedResponse) {
				t.Fatalf("Expected response %#v, but received %#v instead", expectedResponse, resp)
			}
			if util.IsValidClusterToken("worker-token") {
				t.Fatalf("Expected worker-token to not be a valid cluster token after being used, but it is")
			}
			if !util.IsValidCertificateRequestToken("worker-token-kubelet") {
				t.Fatal("Expected worker-token-kubelet to be a valid certificate request token, but it is not")
			}
			if !util.IsValidCertificateRequestToken("worker-token-proxy") {
				t.Fatal("Expected worker-token-proxy to be a valid certificate request token, but it is not")
			}
			expectedCommands := []string{
				"testdata/microk8s-kubectl.wrapper apply -f testdata/args/cni-network/cni.yaml",
			}
			if !reflect.DeepEqual(expectedCommands, m.CalledWithCommand) {
				t.Fatalf("Expected commands %#v, but %#v was executed", expectedCommands, m.CalledWithCommand)
			}
			if !util.HasNoCertsReissueLock() {
				t.Fatal("Expected certificate reissue lock to be in place after successful join, but it is not")
			}
		})(t)
	})
}

// TestJoinFirstNode tests responses when joining a control plane node on a new cluster.
// TestJoinFirstNode mocks the dqlite bind address update and verifies that is is handled properly.
func TestJoinFirstNode(t *testing.T) {
	m := &utiltest.MockRunner{}
	utiltest.WithMockRunner(m, func(t *testing.T) {
		// Create test data
		for file, contents := range map[string]string{
			"testdata/var/lock/ha-cluster":                "",
			"testdata/var/kubernetes/backend/cluster.crt": "DQLITE CERTIFICATE DATA",
			"testdata/var/kubernetes/backend/cluster.key": "DQLITE KEY DATA",
			"testdata/var/kubernetes/backend/info.yaml": `
Address: 127.0.0.1:19001
ID: 1238719276943521
Role: 0
`,
			"testdata/var/kubernetes/backend/cluster.yaml": `
- Address: 127.0.0.1:19001
  ID: 1238719276943521
  Role: 0
`,
			"testdata/certs/ca.crt":                    "CA CERTIFICATE DATA",
			"testdata/certs/ca.key":                    "CA KEY DATA",
			"testdata/certs/serviceaccount.key":        "SERVICE ACCOUNT KEY DATA",
			"testdata/args/kubelet":                    "kubelet arguments\n",
			"testdata/args/kube-apiserver":             "--secure-port 16443",
			"testdata/args/cluster-agent":              "--bind=0.0.0.0:25000",
			"testdata/args/cni-network/cni.yaml":       `some content here. "first-found"`,
			"testdata/credentials/cluster-tokens.txt":  "control-plane-token\n",
			"testdata/credentials/callback-tokens.txt": "",
			"testdata/credentials/callback-token.txt":  "callback-token",
			"testdata/credentials/known_tokens.csv": `kube-proxy-token,system:kube-proxy,kube-proxy,
admin-token-123,admin,admin,"system:masters"
`,
		} {
			if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
				t.Fatalf("Failed to create test directory: %s", err)
			}
			if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
				t.Fatalf("Failed to create test file: %s", err)
			}
			defer os.RemoveAll(filepath.Dir(file))
		}
		defer os.RemoveAll("testdata/var")

		go func() {
			// update cluster with new address after a second
			<-time.After(time.Second)
			newCluster := `
- Address: 10.10.10.10:19001
  ID: 1238719276943521
  Role: 0`
			if err := os.WriteFile("testdata/var/kubernetes/backend/cluster.yaml", []byte(newCluster), 0660); err != nil {
				panic(err)
			}
		}()

		resp, err := v2.Join(context.Background(), v2.JoinRequest{
			ClusterToken:     "control-plane-token",
			RemoteHostName:   "some-invalid-hostname",
			ClusterAgentPort: "25000",
			HostPort:         "10.10.10.10:25000",
			RemoteAddress:    "10.10.10.13:41532",
			WorkerOnly:       false,
		})
		if err != nil {
			t.Fatalf("Expected no errors, but received %q", err)
		}
		if resp == nil {
			t.Fatal("Expected a response but received nil instead")
		}

		expectedResponse := &v2.JoinResponse{
			CertificateAuthority:     "CA CERTIFICATE DATA",
			CallbackToken:            "callback-token",
			APIServerPort:            "16443",
			KubeletArgs:              "kubelet arguments\n\n--hostname-override=10.10.10.13",
			HostNameOverride:         "10.10.10.13",
			DqliteVoterNodes:         []string{"10.10.10.10:19001"},
			ServiceAccountKey:        "SERVICE ACCOUNT KEY DATA",
			CertificateAuthorityKey:  func(s string) *string { return &s }("CA KEY DATA"),
			AdminToken:               "admin-token-123",
			DqliteClusterCertificate: "DQLITE CERTIFICATE DATA",
			DqliteClusterKey:         "DQLITE KEY DATA",
		}
		if !reflect.DeepEqual(*resp, *expectedResponse) {
			t.Fatalf("Expected response %#v, but received %#v instead", expectedResponse, resp)
		}
		if util.IsValidClusterToken("control-plane-token") {
			t.Fatalf("Expected control-plane-token to not be a valid cluster token after being used, but it is")
		}
		s, err := util.ReadFile("testdata/var/kubernetes/backend/update.yaml")
		if err != nil {
			t.Fatalf("Failed to read dqlite update yaml file: %q", err)
		} else if strings.TrimSpace(s) != "Address: 10.10.10.10:19001" {
			t.Fatalf("Expected dqlite update address does not match (%q and %q)", strings.TrimSpace(s), "Address: 10.10.10.10.19001")
		}

		expectedCommands := []string{
			"snapctl restart microk8s.daemon-k8s-dqlite",
			"testdata/microk8s-kubectl.wrapper apply -f testdata/args/cni-network/cni.yaml",
		}
		if !reflect.DeepEqual(expectedCommands, m.CalledWithCommand) {
			t.Fatalf("Expected commands %#v to be called, but received %#v", expectedCommands, m.CalledWithCommand)
		}
		if !util.HasNoCertsReissueLock() {
			t.Fatal("Expected certificate reissue lock to be in place after successful join, but it is not")
		}
	})(t)
}

func TestUnmarshalWorkerOnlyField(t *testing.T) {
	for _, tc := range []struct {
		b             string
		expectedValue v2.WorkerOnlyField
	}{
		{b: "true", expectedValue: true},
		{b: "false", expectedValue: false},
		{b: "null", expectedValue: false},
		{b: `"as-worker"`, expectedValue: true},
		{b: `"as-controlplane"`, expectedValue: false},
	} {
		t.Run(tc.b, func(t *testing.T) {
			var v v2.WorkerOnlyField
			if err := json.Unmarshal([]byte(tc.b), &v); err != nil {
				t.Fatalf("Expected no error but received %q", err)
			}
			if v != tc.expectedValue {
				t.Fatalf("Expected value to be %v, but it was %v", tc.expectedValue, v)
			}
		})
	}
}
