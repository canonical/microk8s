package v1

import (
	"context"
	"fmt"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

// UpgradeRequest is the request message for the v1/upgrade endpoint.
type UpgradeRequest struct {
	// CallbackToken is the callback token used to authenticate the request.
	CallbackToken string `json:"callback"`
	// UpgradeName is the name of the upgrade to perform. Upgrades are listed in the `upgrade-scripts` directory,
	// for example "000-switch-to-calico".
	UpgradeName string `json:"upgrade"`
	// UpgradePhase is the current phase of the upgrade to perform. We do cluster upgrades with a 2-phase commit
	// mechanism. This can be "prepare", "commit", or "rollback".
	UpgradePhase string `json:"phase"`
}

// Upgrade implements "POST v1/upgrade".
func (a *API) Upgrade(ctx context.Context, req UpgradeRequest) error {
	if !util.IsValidSelfCallbackToken(req.CallbackToken) {
		return fmt.Errorf("invalid callback token")
	}
	switch req.UpgradePhase {
	case "prepare", "commit", "rollback":
	default:
		return fmt.Errorf("unknown upgrade phase %q", req.UpgradePhase)
	}
	scriptName := util.SnapPath("upgrade-scripts", req.UpgradeName, fmt.Sprintf("%s-node.sh", req.UpgradePhase))
	if !util.FileExists(scriptName) {
		return fmt.Errorf("could not find script %s", scriptName)
	}

	if err := util.RunCommand(ctx, scriptName); err != nil {
		return fmt.Errorf("failed to execute %s: %q", scriptName, err)
	}
	return nil
}
