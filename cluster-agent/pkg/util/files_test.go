package util_test

import (
	"os"
	"testing"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

func TestFileExists(t *testing.T) {
	_, err := os.Create("testdata/myfile")
	if err != nil {
		t.Fatal("Failed to create test file")
	}

	if !util.FileExists("testdata/myfile") {
		t.Fatal("File should exist but it does not")
	}

	if err := os.Remove("testdata/myfile"); err != nil {
		t.Fatalf("Failed to delete test file: %s", err)
	}

	if util.FileExists("testdata/myfile") {
		t.Fatal("File should not exist but it does")
	}
}

func TestReadFile(t *testing.T) {
	if err := os.WriteFile("testdata/test-read-file", []byte(`my text`), 0644); err != nil {
		t.Fatal("Failed to create test file")
	}

	contents, err := util.ReadFile("testdata/test-read-file")
	if err != nil {
		t.Fatalf("Failed to read test file: %s", err)
	}
	if contents != "my text" {
		t.Fatalf("Test file should contain 'my test' but it contained '%s'", contents)
	}
	os.Remove("testdata/test-read-file")
}
