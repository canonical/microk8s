package util_test

import (
	"context"
	"strings"
	"testing"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

type mockRunner struct {
	calledWithCtx     context.Context
	calledWithCommand string
	err               error
}

func (m *mockRunner) run(ctx context.Context, command []string) error {
	m.calledWithCommand = strings.Join(command, " ")
	m.calledWithCtx = ctx
	return m.err
}

func TestExec(t *testing.T) {
	t.Run("Success", func(t *testing.T) {
		err := util.RunCommand(context.Background(), []string{"/bin/bash", "-c", "exit 0"})
		if err != nil {
			t.Fatalf("Expected no errors, but received %q", err)
		}
	})

	t.Run("Failure", func(t *testing.T) {
		err := util.RunCommand(context.Background(), []string{"/bin/bash", "-c", "exit 1"})
		if err == nil {
			t.Fatal("Expected an error, but did not receive any")
		}
	})

	t.Run("Cancel", func(t *testing.T) {
		ch := make(chan struct{}, 1)
		ctx, cancel := context.WithCancel(context.Background())
		var err error
		go func() {
			err = util.RunCommand(ctx, []string{"sleep", "10"})
			ch <- struct{}{}
		}()
		cancel()
		<-ch
		if err == nil {
			t.Fatal("Expected an error, but did not receive any")
		}
	})
}
