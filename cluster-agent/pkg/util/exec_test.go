package util_test

import (
	"context"
	"testing"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

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
