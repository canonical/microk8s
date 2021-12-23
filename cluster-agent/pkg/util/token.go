package util

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	alpha  string = "abcdefghijklmnopqrstuvqxyzABCDEFGHIJKLMONPQRSTUVWXYZ1234567890"
	digits string = "0123456789"
)

func newRandomString(letters string, length int) string {
	maxInt := big.NewInt(int64(len(letters)))
	s := make([]byte, length)
	for i := range s {
		n, err := rand.Int(rand.Reader, maxInt)
		if err != nil {
			// this should never happen, just pick something pseudorandom as fallback
			s[i] = letters[(i*3+37)%len(letters)]
		}
		s[i] = letters[n.Int64()]
	}
	return string(s)
}

func isValidToken(token string, tokensFile string) bool {
	if token == "" {
		return false
	}
	token = strings.TrimSpace(token)
	if b, err := os.ReadFile(tokensFile); err == nil {
		knownTokens := strings.Split(string(b), "\n")
		for _, knownToken := range knownTokens {
			parts := strings.SplitN(strings.TrimSpace(knownToken), "|", 2)
			if parts[0] != token {
				continue
			}
			if len(parts) == 1 {
				return true
			}
			// token with expiry
			if len(parts) == 2 {
				timestamp, err := strconv.ParseInt(parts[1], 10, 64)
				if err != nil {
					return false
				}
				return time.Now().Before(time.Unix(timestamp, 0))
			}
		}
	}
	return false
}

func appendToken(token string, tokensFile string) error {
	f, err := os.OpenFile(tokensFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0660)
	if err != nil {
		return fmt.Errorf("failed to open %s: %w", tokensFile, err)
	}
	defer f.Close()
	if _, err := f.WriteString(fmt.Sprintf("%s\n", token)); err != nil {
		return fmt.Errorf("failed to append token to %s: %w", tokensFile, err)
	}
	// TODO: consider whether permissions should be 0600 instead
	SetupPermissions(tokensFile)
	return nil
}

func removeToken(token string, tokensFile string) error {
	b, err := os.ReadFile(tokensFile)
	if err != nil {
		return fmt.Errorf("failed to read %s: %w", tokensFile, err)
	}
	existingTokens := strings.Split(string(b), "\n")
	if len(existingTokens) == 0 {
		return nil
	}
	newTokens := make([]string, 0, len(existingTokens))
	for _, tokenInFile := range existingTokens {
		// TODO: this raised an issue with dummy tokens with the same prefix being removed
		// This should not be an issue in real-life.
		if strings.HasPrefix(tokenInFile, token) {
			continue
		}
		newTokens = append(newTokens, tokenInFile)
	}
	if err = os.WriteFile(tokensFile, []byte(strings.Join(newTokens, "\n")), 0660); err != nil {
		return fmt.Errorf("failed to write %s: %w", tokensFile, err)
	}
	// TODO: consider whether permissions should be 0600 instead
	SetupPermissions(tokensFile)
	return nil
}

// IsValidClusterToken checks whether a token is a valid MicroK8s cluster token.
func IsValidClusterToken(token string) bool {
	return isValidToken(token, SnapDataPath("credentials", "cluster-tokens.txt"))
}

// IsValidCertificateRequestToken checks whether a token is a valid MicroK8s certificate request token.
func IsValidCertificateRequestToken(token string) bool {
	return isValidToken(token, SnapDataPath("credentials", "certs-request-tokens.txt"))
}

// IsValidCallbackToken checks whether a token is a valid MicroK8s callback token.
func IsValidCallbackToken(clusterAgentEndpoint, token string) bool {
	return isValidToken(fmt.Sprintf("%s %s", clusterAgentEndpoint, token), SnapDataPath("credentials", "callback-tokens.txt"))
}

// IsValidSelfCallbackToken checks whether the supplied token is the callback token of the current MicroK8s node.
func IsValidSelfCallbackToken(token string) bool {
	return isValidToken(token, SnapDataPath("credentials", "callback-token.txt"))
}

// RemoveClusterToken removes a token from the known cluster tokens.
func RemoveClusterToken(token string) error {
	return removeToken(token, SnapDataPath("credentials", "cluster-tokens.txt"))
}

// RemoveCertificateRequestToken removes a token from the known certificate request tokens.
func RemoveCertificateRequestToken(token string) error {
	return removeToken(token, SnapDataPath("credentials", "certs-request-tokens.txt"))
}

// AddCertificateRequestToken appends a new token that can be used to issue a certificate signing request.
func AddCertificateRequestToken(token string) error {
	return appendToken(token, SnapDataPath("credentials", "certs-request-tokens.txt"))
}

// AddCallbackToken appends a new token that can be used to issue requests to a remote cluster agent.
func AddCallbackToken(clusterAgentEndpoint, token string) error {
	return appendToken(fmt.Sprintf("%s %s", clusterAgentEndpoint, token), SnapDataPath("credentials", "callback-tokens.txt"))
}

// GetKnownToken retrieves the known token of a user from the known_tokens file.
func GetKnownToken(user string) (string, error) {
	allTokens, err := ReadFile(SnapDataPath("credentials", "known_tokens.csv"))
	if err != nil {
		return "", fmt.Errorf("failed to retrieve known token for user %s: %w", user, err)
	}
	for _, line := range strings.Split(allTokens, "\n") {
		line = strings.TrimSpace(line)
		parts := strings.SplitN(line, ",", 3)
		if len(parts) >= 2 && parts[1] == user {
			return parts[0], nil
		}
	}
	return "", fmt.Errorf("no known token found for user %s", user)
}

// GetOrCreateKubeletToken retrieves the kubelet token for a Kubernetes node.
// The existing token is returned (if any), otherwise a new one is created and appended to the known_tokens file.
func GetOrCreateKubeletToken(hostname string) (string, error) {
	user := fmt.Sprintf("system:node:%s", hostname)
	existingToken, err := GetKnownToken(user)
	if err == nil {
		return existingToken, nil
	}

	token := newRandomString(alpha, 32)
	uid := newRandomString(digits, 8)

	if err := appendToken(fmt.Sprintf("%s,%s,kubelet-%s,\"system:nodes\"", token, user, uid), SnapDataPath("credentials", "known_tokens.csv")); err != nil {
		return "", fmt.Errorf("failed to add new kubelet token for %s: %w", user, err)
	}

	return token, nil
}
