package util

import (
	"context"
	"fmt"
	"os/exec"
)

var (
	// CommandRunner is a function that executes a command with a context.
	CommandRunner func(ctx context.Context, command []string) error
)

// RunCommand executes a command with a given context.
// RunCommand returns nil if the command completes successfully and the exit code is 0.
func RunCommand(ctx context.Context, command []string) error {
	return CommandRunner(ctx, command)
}

// DefaultCommandRunner executes a shell command.
func DefaultCommandRunner(ctx context.Context, command []string) error {
	var args []string
	if len(command) > 1 {
		args = command[1:]
	}
	cmd := exec.CommandContext(ctx, command[0], args...)
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("command %v failed with exit code %d: %w", command, cmd.ProcessState.ExitCode(), err)
	}
	return nil
}

func init() {
	CommandRunner = DefaultCommandRunner
}
