package v1_test

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
	"github.com/canonical/microk8s/cluster-agent/pkg/util"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
)

func TestJoin(t *testing.T) {
	m := &utiltest.MockRunner{}
	utiltest.WithMockRunner(m, func(t *testing.T) {
		// Create test data
		for file, contents := range map[string]string{
			"testdata/certs/ca.crt":                    "CA CERTIFICATE DATA",
			"testdata/args/kubelet":                    "kubelet arguments\n",
			"testdata/args/etcd":                       "--listen-client-urls=https://0.0.0.0:12379",
			"testdata/args/kube-apiserver":             "--secure-port 16443",
			"testdata/credentials/cluster-tokens.txt":  "valid-cluster-token\nvalid-other-token\n",
			"testdata/credentials/callback-tokens.txt": "",
			"testdata/credentials/known_tokens.csv": `kube-proxy-token,system:kube-proxy,kube-proxy,
admin-token,admin,admin,"system:masters"
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

		t.Run("InvalidToken", func(t *testing.T) {
			resp, err := v1.Join(context.Background(), v1.JoinRequest{
				ClusterToken: "invalid-token",
			})
			if resp != nil {
				t.Fatalf("Expected a nil response due to invalid token, but got %#v\n", resp)
			}
			if err == nil {
				t.Fatal("Expected an error due to invalid token, but did not get any")
			}
		})

		t.Run("Dqlite", func(t *testing.T) {
			if err := os.MkdirAll("testdata/var/lock", 0755); err != nil {
				t.Fatalf("Failed to create lock directory: %s", err)
			}
			if _, err := os.Create("testdata/var/lock/ha-cluster"); err != nil {
				os.RemoveAll("testdata/var")
				t.Fatalf("Failed to create dqlite lock file: %s", err)
			}
			resp, err := v1.Join(context.Background(), v1.JoinRequest{
				ClusterToken: "valid-other-token",
			})
			os.RemoveAll("testdata/var")
			if resp != nil {
				t.Fatalf("Expected a nil response due to invalid token, but got %#v\n", resp)
			}
			if err == nil {
				t.Fatal("Expected an error due to invalid token, but did not get any")
			}
		})

		t.Run("Success", func(t *testing.T) {
			if err := os.MkdirAll("testdata/var/lock", 0755); err != nil {
				t.Fatalf("Failed to create lock directory: %s", err)
			}
			defer os.RemoveAll("testdata/var")
			resp, err := v1.Join(context.Background(), v1.JoinRequest{
				ClusterToken:     "valid-cluster-token",
				HostName:         "my-hostname",
				ClusterAgentPort: "25000",
				RemoteAddress:    "10.10.10.10:41422",
				CallbackToken:    "callback-token",
			})
			if err != nil {
				t.Fatalf("Expected no errors, but got %s", err)
			}
			if resp == nil {
				t.Fatal("Expected non-nil response")
			}
			expectedResponse := &v1.JoinResponse{
				CertificateAuthority: "CA CERTIFICATE DATA",
				EtcdEndpoint:         "https://0.0.0.0:12379",
				APIServerPort:        "16443",
				KubeProxyToken:       "kube-proxy-token",
				KubeletArgs:          "kubelet arguments\n\n--hostname-override=10.10.10.10",
				KubeletToken:         resp.KubeletToken,
				HostNameOverride:     "10.10.10.10",
			}
			if *resp != *expectedResponse {
				t.Fatalf("Expected response %#v, but it was %#v", expectedResponse, resp)
			}
			if len(resp.KubeletToken) != 32 {
				t.Fatalf("Expected kubelet token %q to have length 32", resp.KubeletToken)
			}
			if util.IsValidClusterToken("valid-cluster-token") {
				t.Fatal("Expected cluster token to not be valid after successful join, but it is")
			}
			if len(m.CalledWithCommand) != 1 || m.CalledWithCommand[0] != "snapctl restart microk8s.daemon-apiserver" {
				t.Fatalf("Expected API server restart command, but got %q", m.CalledWithCommand)
			}

			kubeletToken, err := util.GetKnownToken("system:node:10.10.10.10")
			if err != nil {
				t.Fatalf("Expected no error when retrieving kubelet token, but received %q", err)
			}
			if kubeletToken != resp.KubeletToken {
				t.Fatalf("Expected kubelet known token to match response, but they do not (%q != %q)", kubeletToken, resp.KubeletToken)
			}

			if !util.IsValidCallbackToken("10.10.10.10:25000", "callback-token") {
				t.Fatal("Expected callback-token to be a valid callback token, but it is not")
			}
			if !util.IsValidCertificateRequestToken("valid-cluster-token") {
				t.Fatal("Expected valid-cluster-token to be a valid certificate request token, but it is not")
			}
			if !util.HasNoCertsReissueLock() {
				t.Fatal("Expected certificate reissue lock to be in place after successful join, but it is not")
			}
		})

	})(t)
}
