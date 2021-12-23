package utiltest

import (
	"context"
	"strings"
	"testing"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

type MockRunner struct {
	CalledWithCtx     context.Context
	CalledWithCommand string
	Err               error
}

func (m *MockRunner) Run(ctx context.Context, command []string) error {
	m.CalledWithCommand = strings.Join(command, " ")
	m.CalledWithCtx = ctx
	return m.Err
}

// WithMockRunner runs a test with a mock command runner applied.
func WithMockRunner(m *MockRunner, f func(*testing.T)) func(*testing.T) {
	return func(t *testing.T) {
		util.CommandRunner = m.Run
		f(t)
		util.CommandRunner = util.DefaultCommandRunner
	}
}
