package util

import (
	"context"
	"fmt"
	"os/exec"
)

// SignCertificate signs a certificate request using the MicroK8s CA.
// It returns the signed certificate, or an error.
func SignCertificate(ctx context.Context, certificateRequest string) (string, error) {
	signCmd := exec.CommandContext(ctx,
		"openssl", "x509", "-sha256", "-req",
		"-CA", SnapDataPath("certs", "ca.crt"), "-CAkey", SnapDataPath("certs", "ca.key"),
		"-CAcreateserial", "-days", "3650",
	)

	stdin, err := signCmd.StdinPipe()
	if err != nil {
		return "", fmt.Errorf("could not create stdin pipe for sign command: %q", err)
	}

	if _, err := stdin.Write([]byte(certificateRequest)); err != nil {
		return "", fmt.Errorf("could not write certificate request to sign command: %q", err)
	}

	certificateBytes, err := signCmd.Output()
	if err != nil {
		return "", fmt.Errorf("could not retrieve command output: %q", err)
	}

	return string(certificateBytes), nil
}
