package util

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
)

// kubectlGetNodesJSON parses the output of the "kubectl get nodes -o json" command.
type kubectlGetNodesJSON struct {
	Items []struct {
		Status struct {
			Addresses []struct {
				Address string `json:"address"`
				Type    string `json:"type"`
			} `json:"addresses"`
		} `json:"status"`
	} `json:"items"`
}

func parseControlPlaneNodeIPs(jsonOutput []byte) ([]string, error) {
	var response kubectlGetNodesJSON
	if err := json.Unmarshal(jsonOutput, &response); err != nil {
		return nil, fmt.Errorf("failed to parse kubectl command output: %w", err)
	}

	nodes := make([]string, 0, len(response.Items))
	for _, item := range response.Items {
		for _, address := range item.Status.Addresses {
			if address.Type == "InternalIP" {
				nodes = append(nodes, address.Address)
			}
		}
	}

	return nodes, nil
}

// ListControlPlaneNodeIPs returns the internal IPs of the control plane nodes of the MicroK8s cluster.
func ListControlPlaneNodeIPs(ctx context.Context) ([]string, error) {
	cmd := exec.CommandContext(
		ctx,
		SnapPath("microk8s-kubectl.wrapper"), "get", "nodes",
		"-l", "node.kubernetes.io/microk8s-controlplane=microk8s-controlplane",
		"-o", "json",
	)

	stdout, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("failed to execute kubectl command: %w", err)
	}

	return parseControlPlaneNodeIPs(stdout)
}
