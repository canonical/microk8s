package v1_test

import (
	"context"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
	"github.com/canonical/microk8s/cluster-agent/pkg/util"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
)

func TestConfigure(t *testing.T) {
	for file, contents := range map[string]string{
		"testdata/args/kube-apiserver":            "--key=value\n--old=to-remove",
		"testdata/args/kube-proxy":                "--key=value2",
		"testdata/credentials/callback-token.txt": "valid-token",
	} {
		if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
			t.Fatalf("Failed to create test directory: %s", err)
		}
		if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
			t.Fatalf("Failed to create test file: %s", err)
		}
		defer os.RemoveAll(filepath.Dir(file))
	}

	m := &utiltest.MockRunner{}
	utiltest.WithMockRunner(m, func(t *testing.T) {
		t.Run("InvalidToken", func(t *testing.T) {
			err := v1.Configure(context.Background(), v1.ConfigureRequest{
				CallbackToken: "invalid-token",
				ConfigureServices: []v1.ConfigureServiceRequest{
					{Name: "kube-apiserver", Restart: true},
				},
			})
			if err == nil {
				t.Fatal("Expected an error but did not receive any")
			}
			if len(m.CalledWithCommand) > 0 {
				t.Fatalf("Expected no commands to be called, but received %#v", m.CalledWithCommand)
			}
		})
	})(t)

	for _, tc := range []struct {
		name              string
		req               v1.ConfigureRequest
		expectedCommands  []string
		expectedArguments map[string]map[string]string
	}{
		{
			name: "update-services-add-addons",
			req: v1.ConfigureRequest{
				CallbackToken: "valid-token",
				ConfigureServices: []v1.ConfigureServiceRequest{
					{Name: "kube-apiserver", UpdateArguments: []map[string]string{{"--key": "new-value"}}, RemoveArguments: []string{"--old"}, Restart: false},
					{Name: "kube-proxy", Restart: true},
				},
				ConfigureAddons: []v1.ConfigureAddonRequest{
					{Name: "dns", Enable: true},
					{Name: "ingress", Disable: true},
					{Name: "other"},
				},
			},
			expectedCommands: []string{
				"snapctl restart microk8s.daemon-proxy",
				"testdata/microk8s-enable.wrapper dns",
				"testdata/microk8s-disable.wrapper ingress",
			},
			expectedArguments: map[string]map[string]string{
				"kube-apiserver": {
					"--key": "new-value",
					"--old": "",
				},
			},
		},
	} {
		t.Run(tc.name, func(t *testing.T) {
			m := &utiltest.MockRunner{}
			utiltest.WithMockRunner(m, func(t *testing.T) {
				if err := v1.Configure(context.Background(), tc.req); err != nil {
					t.Fatalf("Expected no errors but received %q", err)
				}
				for serviceName, expectedArguments := range tc.expectedArguments {
					for key, expectedValue := range expectedArguments {
						if value := util.GetServiceArgument(serviceName, key); value != expectedValue {
							t.Fatalf("Expected argument %q of service %q to be %q, but it is %q", key, serviceName, expectedValue, value)
						}
					}
				}
				if !reflect.DeepEqual(tc.expectedCommands, m.CalledWithCommand) {
					t.Fatalf("Expected commands %#v but %#v was executed instead", tc.expectedCommands, m.CalledWithCommand)
				}
			})(t)
		})
	}
}
