package v2_test

import "context"

func mockListControlPlaneNodes(nodes ...string) func(ctx context.Context) ([]string, error) {
	return func(ctx context.Context) ([]string, error) {
		return nodes, nil
	}
}
