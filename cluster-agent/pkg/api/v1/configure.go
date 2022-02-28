package v1

import (
	"bytes"
	"context"
	"fmt"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

// RestartServiceField is the "restart" field of the ConfigureServiceRequest message.
type RestartServiceField bool

// UnmarshalJSON implements json.Unmarshaler.
// It handles both boolean values, as well as the string value "yes".
func (v *RestartServiceField) UnmarshalJSON(b []byte) error {
	*v = RestartServiceField(bytes.Equal(b, []byte("true")) || bytes.Equal(b, []byte(`"yes"`)))
	return nil
}

// ConfigureServiceRequest is a configuration request for MicroK8s.
type ConfigureServiceRequest struct {
	// Name is the service name.
	Name string `json:"name"`
	// UpdateArguments is a map of arguments to be updated.
	UpdateArguments []map[string]string `json:"arguments_update"`
	// RemoveArguments is a list of arguments to remove.
	RemoveArguments []string `json:"arguments_remove"`
	// Restart defines whether the service should be restarted.
	Restart RestartServiceField `json:"restart"`
}

// ConfigureAddonRequest is a configuration request for a MicroK8s addon.
type ConfigureAddonRequest struct {
	// Name is the name of the addon.
	Name string `json:"name"`
	// Enable is true if we want to enable the addon.
	Enable bool `json:"enable"`
	// Disable is true if we want to disable the addon.
	Disable bool `json:"disable"`
}

// ConfigureRequest is the request message for the v1/configure endpoint.
type ConfigureRequest struct {
	// CallbackToken is the callback token used to authenticate the request.
	CallbackToken string `json:"callback"`

	// ConfigureServices is a list of configuration updates for the MicroK8s services.
	ConfigureServices []ConfigureServiceRequest `json:"service"`

	// ConfigureAddons is a list of addons to manage
	ConfigureAddons []ConfigureAddonRequest `json:"addon"`
}

// Configure implements "POST /CLUSTER_API_V1/configure".
func Configure(ctx context.Context, req ConfigureRequest) error {
	if !util.IsValidSelfCallbackToken(req.CallbackToken) {
		return fmt.Errorf("invalid callback token")
	}
	for _, service := range req.ConfigureServices {
		if err := util.UpdateServiceArguments(service.Name, service.UpdateArguments, service.RemoveArguments); err != nil {
			return fmt.Errorf("failed to update arguments of service %q: %w", service.Name, err)
		}
		if service.Restart {
			if err := util.RestartService(ctx, service.Name); err != nil {
				return fmt.Errorf("failed to restart service %q: %w", service.Name, err)
			}
		}
	}

	for _, addon := range req.ConfigureAddons {
		switch {
		case addon.Enable:
			if err := util.RunCommand(ctx, []string{util.SnapPath("microk8s-enable.wrapper"), addon.Name}); err != nil {
				return fmt.Errorf("failed to enable addon %q: %w", addon.Name, err)
			}
		case addon.Disable:
			if err := util.RunCommand(ctx, []string{util.SnapPath("microk8s-disable.wrapper"), addon.Name}); err != nil {
				return fmt.Errorf("failed to disable addon %q: %w", addon.Name, err)
			}
		}
	}
	return nil
}
