package util_test

import (
	"fmt"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

func TestClusterTokens(t *testing.T) {
	os.RemoveAll("testdata/credentials")
	t.Run("MissingTokensFile", func(t *testing.T) {
		if util.IsValidClusterToken("token1") {
			t.Fatal("Expected token1 to not be valid, but it is")
		}
		if err := util.RemoveClusterToken("token1"); err == nil {
			t.Fatal("Expected an error when removing a missing cluster token, but did not receive any")
		}
	})
	if err := os.MkdirAll("testdata/credentials", 0755); err != nil {
		t.Fatal("Failed to create test directory")
	}
	defer os.RemoveAll("testdata/credentials")
	now := time.Now().Unix()
	clusterTokens := fmt.Sprintf(`
token1
token-invalid-timestamp|-10a
token-expired|%d
token-not-expired|%d
`, now-300, now+300)

	if err := os.WriteFile("testdata/credentials/cluster-tokens.txt", []byte(clusterTokens), 0600); err != nil {
		t.Fatalf("Failed to create test cluster-tokens.txt file: %s", err)
	}

	for _, tc := range []struct {
		token         string
		expectedValid bool
	}{
		{token: "token1", expectedValid: true},
		{token: "token-expired", expectedValid: false},
		{token: "token-not-expired", expectedValid: true},
		{token: "missing-token", expectedValid: false},
		{token: "token-invalid-timestamp", expectedValid: false},
	} {
		t.Run(tc.token, func(t *testing.T) {
			if util.IsValidClusterToken(tc.token) != tc.expectedValid {
				if tc.expectedValid {
					t.Fatalf("Token %s should be valid, but it is not", tc.token)
				} else {
					t.Fatalf("Token %s should not be valid, but it is", tc.token)
				}
			}
		})
	}

	t.Run("RemoveOne", func(t *testing.T) {
		if err := util.RemoveClusterToken("token1"); err != nil {
			t.Fatalf("Failed to remove cluster token: %s", err)
		}
		if util.IsValidClusterToken("token1") {
			t.Fatal("Cluster token token1 should not be valid after removal, but it is")
		}
		if !util.IsValidClusterToken("token-not-expired") {
			t.Fatal("Cluster token token-not-expired should be valid after removal of other token, but it is not")
		}
	})

	t.Run("RemoveAll", func(t *testing.T) {
		for _, token := range []string{"token1", "token-not-expired", "missing"} {
			t.Run(token, func(t *testing.T) {
				if err := util.RemoveClusterToken(token); err != nil {
					t.Fatalf("Failed to remove cluster token %s: %s", token, err)
				}
				if util.IsValidClusterToken(token) {
					t.Fatalf("Cluster token %s should not be valid after removal, but it is", token)
				}
			})
		}
	})
}

func TestCertificateRequestTokens(t *testing.T) {
	if err := os.MkdirAll("testdata/credentials", 0755); err != nil {
		t.Fatalf("Failed to create test directory: %s", err)
	}
	defer os.RemoveAll("testdata/credentials")
	if err := util.AddCertificateRequestToken("my-token"); err != nil {
		t.Fatalf("Failed to add certificate request token: %s", err)
	}
	contents, err := util.ReadFile("testdata/credentials/certs-request-tokens.txt")
	if err != nil {
		t.Fatalf("Failed to retrieve tokens: %s", err)
	}
	if !strings.Contains(contents, "my-token\n") {
		t.Fatal("Expected my-token to exist in tokens file, but it did not")
	}
	if !util.IsValidCertificateRequestToken("my-token") {
		t.Fatal("Expected my-token to be a valid certificate request token, but it is not")
	}
}

func TestCallbackTokens(t *testing.T) {
	if err := os.MkdirAll("testdata/credentials", 0755); err != nil {
		t.Fatalf("Failed to create test directory: %s", err)
	}
	defer os.RemoveAll("testdata/credentials")
	if err := util.AddCallbackToken("ip:port", "my-token"); err != nil {
		t.Fatalf("Failed to add certificate request token: %s", err)
	}
	contents, err := util.ReadFile("testdata/credentials/callback-tokens.txt")
	if err != nil {
		t.Fatalf("Failed to retrieve tokens: %s", err)
	}
	if !strings.Contains(contents, "ip:port my-token\n") {
		t.Fatal("Expected my-token to exist in tokens file, but it did not")
	}
	if !util.IsValidCallbackToken("ip:port", "my-token") {
		t.Fatal("Expected my-token to be a valid callback token for ip:port, but it is not")
	}
}

func TestKnownTokens(t *testing.T) {
	if err := os.MkdirAll("testdata/credentials", 0755); err != nil {
		t.Fatalf("Failed to create test directory: %s", err)
	}
	defer os.RemoveAll("testdata/credentials")
	if token, err := util.GetKnownToken("user"); token != "" || err == nil {
		t.Fatalf("Expected an empty token and an error, but found token %s and error %s", token, err)
	}

	contents := `
token1,system:kube-proxy,kube-proxy,
token2,system:node:existing-host,kubelet-0123,"system:nodes"
`
	if err := os.WriteFile("testdata/credentials/known_tokens.csv", []byte(contents), 0600); err != nil {
		t.Fatalf("Failed to create file with known tokens: %s", err)
	}
	for _, tc := range []struct {
		user        string
		expectToken string
		expectError bool
	}{
		{user: "missing-user", expectError: true},
		{user: "system:kube-proxy", expectToken: "token1"},
		{user: "system:node:existing-host", expectToken: "token2"},
	} {
		t.Run(tc.user, func(t *testing.T) {
			token, err := util.GetKnownToken(tc.user)
			switch {
			case tc.expectError && err == nil:
				t.Fatal("Expected an error but did not get one")
			case !tc.expectError && err != nil:
				t.Fatalf("Expected no errors, but received %q", err)
			case tc.expectToken != token:
				t.Fatalf("Expected token %q but received %q", tc.expectToken, token)
			}
		})
	}
	t.Run("Kubelet", func(t *testing.T) {
		t.Run("Existing", func(t *testing.T) {
			token, err := util.GetOrCreateKubeletToken("existing-host")
			if err != nil {
				t.Fatalf("Expected no errors, but received %q", err)
			}
			if token != "token2" {
				t.Fatalf("Expected token %q, but received %q", "token2", token)
			}
		})
		t.Run("Create", func(t *testing.T) {
			newToken, err := util.GetOrCreateKubeletToken("new-host")
			if err != nil {
				t.Fatalf("Expected no errors, but received %q", err)
			}
			if newToken == "" {
				t.Fatal("Expected token to be not-empty, but it was")
			}
			token, err := util.GetOrCreateKubeletToken("new-host")
			if err != nil {
				t.Fatalf("Expected no errors, but received %q", err)
			}
			if token != newToken {
				t.Fatalf("Expected tokens to match, but they do not (%q != %q)", token, newToken)
			}
		})
	})
}
