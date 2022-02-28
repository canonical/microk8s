package utiltest

import (
	"context"
	"log"
	"strings"
	"testing"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

// MockRunner is a mock implementation of CommandRunner context.
type MockRunner struct {
	CalledWithCtx     context.Context
	CalledWithCommand []string
	Log               bool
	Err               error
}

// Run is a mock implementation of CommandRunner.
func (m *MockRunner) Run(ctx context.Context, command []string) error {
	if m.Log {
		log.Printf("mock execute %#v", command)
	}
	m.CalledWithCommand = append(m.CalledWithCommand, strings.Join(command, " "))
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
