package util

import (
	"context"
	"fmt"
	"net"
	"os"
	"time"

	"gopkg.in/yaml.v2"
)

// DqliteCluster is the format of the dqlite cluster.yaml file.
type DqliteCluster []DqliteClusterNode

// DqliteClusterNode is a node in the dqlite cluster.
type DqliteClusterNode struct {
	// Address is the address of the node in the cluster.
	Address string `yaml:"Address"`
	// ID is the unique identifier of the node in the cluster.
	ID uint64 `yaml:"ID,omitempty"`
	// NodeRole is the role of the node in the cluster.
	// 0 -- Voter
	// 1 -- StandBy
	// 2 -- Spare
	NodeRole int `yaml:"Role,omitempty"`
}

// GetDqliteCluster a list of all currently known dqlite cluster nodes.
func GetDqliteCluster() (DqliteCluster, error) {
	s, err := ReadFile(SnapDataPath("var", "kubernetes", "backend", "cluster.yaml"))
	if err != nil {
		return DqliteCluster{}, fmt.Errorf("failed to read list of dqlite nodes: %w", err)
	}

	cluster := DqliteCluster{}
	if err := yaml.Unmarshal([]byte(s), &cluster); err != nil {
		return DqliteCluster{}, fmt.Errorf("failed to parse list of dqlite nodes: %w", err)
	}

	return cluster, nil
}

// UpdateDqliteIP sets the local dqlite cluster node to bind to a new IP address.
func UpdateDqliteIP(ctx context.Context, host string) error {
	s, err := ReadFile(SnapDataPath("var", "kubernetes", "backend", "info.yaml"))
	if err != nil {
		return fmt.Errorf("failed to retrieve current node info: %w", err)
	}
	var node DqliteClusterNode
	if err := yaml.Unmarshal([]byte(s), &node); err != nil {
		return fmt.Errorf("invalid format for current node info: %w", err)
	}

	_, port, _ := net.SplitHostPort(node.Address)
	nodeUpdate := DqliteClusterNode{
		Address: net.JoinHostPort(host, port),
	}
	b, err := yaml.Marshal(nodeUpdate)
	if err != nil {
		return fmt.Errorf("failed to marshal current node info update: %w", err)
	}

	if err := os.WriteFile(SnapDataPath("var", "kubernetes", "backend", "update.yaml"), b, 0660); err != nil {
		return fmt.Errorf("failed to create dqlite update file: %w", err)
	}

	if err := RestartService(ctx, "k8s-dqlite"); err != nil {
		return fmt.Errorf("failed to restart k8s-dqlite service: %w", err)
	}
	if err := RestartService(ctx, "apiserver"); err != nil {
		return fmt.Errorf("failed to restart apiserver service: %w", err)
	}

	return nil
}

// WaitForDqliteCluster queries the dqlite cluster nodes repeatedly until f(cluster) becomes true.
func WaitForDqliteCluster(ctx context.Context, f func(DqliteCluster) (bool, error)) (DqliteCluster, error) {
	interval := time.NewTicker(time.Second)
	for {
		cluster, err := GetDqliteCluster()
		if err != nil {
			return DqliteCluster{}, err
		}

		ok, err := f(cluster)
		if err != nil {
			return DqliteCluster{}, fmt.Errorf("failed check for cluster condition: %w", err)
		}
		if ok {
			return cluster, nil
		}

		select {
		case <-ctx.Done():
			return DqliteCluster{}, fmt.Errorf("timed out waiting for cluster condition: %w", ctx.Err())
		case <-interval.C:
		}
	}
}
