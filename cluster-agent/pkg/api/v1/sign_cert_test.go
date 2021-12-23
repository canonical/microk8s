package v1_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

var (
	caCrt = `-----BEGIN CERTIFICATE-----
MIIC+zCCAeOgAwIBAgIJAJ+KEbJiY2lGMA0GCSqGSIb3DQEBCwUAMBQxEjAQBgNV
BAMMCTEyNy4wLjAuMTAeFw0xODA1MjExMzA0MjZaFw00NTEwMDYxMzA0MjZaMBQx
EjAQBgNVBAMMCTEyNy4wLjAuMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoC
ggEBAK/KWrGIE5OIvv1M0WCRXSex43vUTfWj27eOO1U5ZvBXzoHQwPE08fttysm7
hiNNFfEhEDKAOQQBfNW36/rXrAxMcTmNsQJSs96sb3FuWJPzMksgqpxPuUmw1Hvt
BttPXcsN5NaJyrPf4al8Hob0UWCG0NNAQ7ClWh8JzuI2o4gw2rK3mmC9OlCVJ2Gl
7weRKWeSOkN2jmojAbneY+aCwDR5vsLa3laA2y1BttMoGAYk9ZF9LBNn4PkjMIVz
yLXboJrXZj8WUJiby85hEMrTzBb0tDWhdSXAkbjhQ84Eg5kQ/798ANb/hypbeAPV
XyzoY8Iy6oh8t10d1L4PKQDpJQkCAwEAAaNQME4wHQYDVR0OBBYEFL6vjXUOUCtR
Te0/4aUdVM/Pil4EMB8GA1UdIwQYMBaAFL6vjXUOUCtRTe0/4aUdVM/Pil4EMAwG
A1UdEwQFMAMBAf8wDQYJKoZIhvcNAQELBQADggEBAIcsDou4Af16TjoqZsDNrz6x
d1wRho30lpMkeVu8TED8XPuVoLLadB72ubTALO1XxwHwLoD7eiWF6X58APoMXAS+
EjrYx/YvIN5cBz27iuBY7sUtLlI65vUxjnUui1lqLhpTOKV+g92U5K3OXpQGWHt7
1tNTkrgEbk5MYgfvtrGLOwAwSM0MXEHxAUjWJYu5TmiJDi92bICe0jpWzV0j9FYq
A21WZExy6MJhdDRD8hbIaugW0d98xZKviVXKjIKoRo7GMopQMed0HoNtxf2yBdXJ
V1sTs6aTl0jpjXx2kzmz+8ioYbBmsnCLGEuKyd7orDFL0elIzOLTmkH18T4WVRo=
-----END CERTIFICATE-----
`
	caKey = `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAr8pasYgTk4i+/UzRYJFdJ7Hje9RN9aPbt447VTlm8FfOgdDA
8TTx+23KybuGI00V8SEQMoA5BAF81bfr+tesDExxOY2xAlKz3qxvcW5Yk/MySyCq
nE+5SbDUe+0G209dyw3k1onKs9/hqXwehvRRYIbQ00BDsKVaHwnO4jajiDDasrea
YL06UJUnYaXvB5EpZ5I6Q3aOaiMBud5j5oLANHm+wtreVoDbLUG20ygYBiT1kX0s
E2fg+SMwhXPItdugmtdmPxZQmJvLzmEQytPMFvS0NaF1JcCRuOFDzgSDmRD/v3wA
1v+HKlt4A9VfLOhjwjLqiHy3XR3Uvg8pAOklCQIDAQABAoIBACBtKkefO0U2r0xY
NDMk/VMKLFU2N189Z5U3Zlh1KzjgaZZmpICZ7J0dho+pyLeQS6DcIXm/T0Ue5SEj
OSNfTzxBiY09Rs6P5OAJXNFGso4wCTH0h6QnzJz8QmXNtjsUK8/98x1j84E0phK2
c4cfYDd3BuRA8XuPNM2O6JuvyoCfe8b22uM5fR9EGBmqZpwlmlByfCpTPw3TQDEh
U0Id20Gfjb3n1SohmHtd6qquI3zaKhahIAhKJMWLEELw+y5V+q0XqzuT1CvIA0nh
FO8u9gMQlYzTX36bMdSTbJQJQhBOTzTJql6VrxSu8Inzj6+r6Z8IPS6PljWfzlI1
tby8UgECgYEA6apCnLQ0mbiu9zThJe+nbpq2obQwPsb87Im8ltKudcuxuK6Ls2Le
/4JNPRdG0wHrL1Aim9XMKghLVPnnjxJaC9cHTL9+iyMiZpJR1Gu7hkrNZrrdMcNH
zhWgYwZhAOpGDTjF/X9YrYQgMiFYylHobALO92G+mcWkCKcrCv3jRkECgYEAwJfp
sk5P/p8H73cbpQ+bfqiWS1AImGssZJdKugJrgKcbbesGRw2puQDGJCBzQVprpVSe
oZNDN7hpctl4p9rAbpqN399fMZJwf/uHDh3qnMoAiXwEhsSb8y7tP+pD8JjNy5on
TYSAgc1oPycowJRdQ6UB+9vpG7lF1PDWLzKP/MkCgYBOAO6XzXi50HNoRxjaRzTH
sZJCTRrF+ju44wo390ESRdugYXR1gA4dkewi9sBH9J4Ef2XuS+MKLRao2Xw5wNCa
nz/qmQqvfB0hzLrQhN5nKFWFc+Afmqc/3uxZ4mlDmvGjvE4sH/UEh9UPpx4y/EDw
vcdFwjWUs+vcj6HI25ShgQKBgQCvnFVdXocWlw/3TFYKxhZ1AWg5t/p+cIsEFefv
gDFiF/2s1nbc5xpxNMF3Q5eUacxp7qTOk6bg8ehE7wNTmuWIdKkVD2qPmwW1zTYy
qxi4aoDe3BSMhk3lCk8Ozp+wjMRp+GAKEN3UfeWmYCCKqT35ZkZOzxDZVLDWH9xN
IP+l8QKBgQCrKw7Lu0IRW2xnd/rGZYy7S45D13tyrdFj3XsEZXUg/CmA0fuQM/fV
0yLryoT7dL/QU840tNE722aZlJWPXi00YZaKfGAboUwA67mZGocyTrcoQipOuLRu
7WOhX3E+uCGY4Hew7Y7yK4IRkUg20TyXvhPakJGZ934mbJVvE3bGsA==
-----END RSA PRIVATE KEY-----
`
	csr = `-----BEGIN CERTIFICATE REQUEST-----
MIIDXTCCAkUCAQAwazELMAkGA1UEBhMCVVMxGTAXBgNVBAgMEElzbGVzIG9mIEJs
ZXNzZWQxEDAOBgNVBAcMB0Fya2FkaWExDTALBgNVBAoMBGFjbWUxDDAKBgNVBAsM
A2RldjESMBAGA1UEAwwJMTI3LjAuMC4xMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A
MIIBCgKCAQEAynlrORb9BSxazS9C3C3p5ZxSMFH8y7H2FWL/ldX7/6GuZTBO8toE
4T9ZWF/852JE06LoS1Odox/RcQQht8g2BfP8L8wOlsHU3wQ2yMjRDpMwFmFe9DWB
7TZyo6lKItzN6IbJkwPp4UmcGa0E1M7wDLvHxuGX8zT8s6YsK16+BrMKb3xXd9iK
2+H8DwqIkNk16vYfTimp/oa9+AQfDahR2aHrIh4Peg7bz2YhYRN4G5yyL0glnKD7
EpcYbAwbTXLigZQJRM+vxCOCxnGcZumisGpzK64G6H2NFYYC5PtYuFERZ+iLVRCH
DP/qLHW4EGAtm4eXMIGPrX9CQ6dPPxnP1QIDAQABoIGsMIGpBgkqhkiG9w0BCQ4x
gZswgZgwgZUGA1UdEQSBjTCBioIKa3ViZXJuZXRlc4ISa3ViZXJuZXRlcy5kZWZh
dWx0ghZrdWJlcm5ldGVzLmRlZmF1bHQuc3Zjgh5rdWJlcm5ldGVzLmRlZmF1bHQu
c3ZjLmNsdXN0ZXKCJGt1YmVybmV0ZXMuZGVmYXVsdC5zdmMuY2x1c3Rlci5sb2Nh
bIcEfwAAAYcECpi3ATANBgkqhkiG9w0BAQsFAAOCAQEAokLa4x2UXxu9n7RYSsfx
LJGsDG6LeAroPxmUFZrPYrwwnkryER14y9yG2DoLTDvSA3TTo6TgU3V9vnsdDx6u
YQneiuXXkVspaGKnxQuxxZSJp2UK6MPqk2V0v6Wt4Dj0JPYYCXeVzcQvB+MvtdY7
ymatND8MEieOehuBWtOtlEXREzPxBcT/uG3MYGri4rHYcIjw7LH1zEkGyoAXxklu
dIJf6OKrAXWJmDRQT+Tvv/ul4fYO5VvNkaCYfDULUifiBPaBI177lsCjueNcHUsL
9QKhbRxw0N1ZCVk2MDkUJRvj4kanwcaiVl96JKJapS3ztVJBo60G2P0crvHTahVZ
OQ==
-----END CERTIFICATE REQUEST-----
`
)

func TestSignCert(t *testing.T) {
	for file, contents := range map[string]string{
		"testdata/certs/ca.crt":                         caCrt,
		"testdata/certs/ca.key":                         caKey,
		"testdata/credentials/certs-request-tokens.txt": "valid-token\nother-token\n",
	} {
		if err := os.MkdirAll(filepath.Dir(file), 0755); err != nil {
			t.Fatalf("Failed to create test directory: %s", err)
		}
		if err := os.WriteFile(file, []byte(contents), 0660); err != nil {
			t.Fatalf("Failed to create test file: %s", err)
		}
		defer os.RemoveAll(filepath.Dir(file))
	}

	t.Run("InvalidToken", func(t *testing.T) {
		resp, err := v1.SignCert(context.Background(), v1.SignCertRequest{
			Token:                     "invalid-token",
			CertificateSigningRequest: csr,
		})
		if err == nil {
			t.Fatal("Expected an error but did not receive any")
		}
		if resp != nil {
			t.Fatalf("Expected a nil response but received %#v", resp)
		}
	})

	t.Run("InvalidRequest", func(t *testing.T) {
		resp, err := v1.SignCert(context.Background(), v1.SignCertRequest{
			Token:                     "valid-token",
			CertificateSigningRequest: "invalid-request",
		})
		if err == nil {
			t.Fatal("Expected an error but did not receive any")
		}
		if resp != nil {
			t.Fatalf("Expected a nil response but received %#v", resp)
		}
		if util.IsValidCertificateRequestToken("valid-token") {
			t.Fatal("Expected valid-token to not be a valid certificate token after use")
		}
	})

	t.Run("Success", func(t *testing.T) {
		resp, err := v1.SignCert(context.Background(), v1.SignCertRequest{
			Token:                     "other-token",
			CertificateSigningRequest: csr,
		})
		if err != nil {
			t.Fatalf("Expected no error but received %q", err)
		}
		if resp == nil {
			t.Fatal("Expected a non-nil response")
		}
		if !strings.HasPrefix(resp.Certificate, "-----BEGIN CERTIFICATE-----") {
			t.Fatal("Expected signed certificate in PEM format", resp.Certificate)
		}
		if util.IsValidCertificateRequestToken("other-token") {
			t.Fatal("Expected other-token to not be a valid certificate token after use")
		}
	})
}
