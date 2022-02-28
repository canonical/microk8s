package v2

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"strings"

	"github.com/canonical/microk8s/cluster-agent/pkg/util"
)

// WorkerOnlyField is the "worker" field of the JoinRequest message.
type WorkerOnlyField bool

// UnmarshalJSON implements json.Unmarshaler.
// It handles boolean values, as well as the string value "as-worker".
func (v *WorkerOnlyField) UnmarshalJSON(b []byte) error {
	*v = WorkerOnlyField(bytes.Equal(b, []byte("true")) || bytes.Equal(b, []byte(`"as-worker"`)))
	return nil
}

// JoinRequest is the request message for the v2/join API endpoint.
type JoinRequest struct {
	// ClusterToken is the token generated during "microk8s add-node".
	ClusterToken string `json:"token"`
	// RemoteHostName is the hostname of the joining host.
	RemoteHostName string `json:"hostname"`
	// ClusterAgentPort is the port number where the cluster-agent is listening on the joining node.
	ClusterAgentPort string `json:"port"`
	// WorkerOnly is true when joining a worker-only node.
	WorkerOnly WorkerOnlyField `json:"worker"`
	// HostPort is the hostname and port that accepted the request. This is retrieved directly from the *http.Request object.
	HostPort string `json:"-"`
	// RemoteAddress is the remote address from which the join request originates. This is retrieved directly from the *http.Request object.
	RemoteAddress string `json:"-"`
}

// JoinResponse is the response message for the v2/join API endpoint.
type JoinResponse struct {
	// CertificateAuthority is the root CertificateAuthority certificate for the Kubernetes cluster.
	CertificateAuthority string `json:"ca"`
	// CallbackToken is a callback token used to authenticate requests with the cluster agent on the joining node.
	CallbackToken string `json:"callback_token"`
	// APIServerPort is the port where the kube-apiserver is listening.
	APIServerPort string `json:"apiport"`
	// KubeletArgs is a string with arguments for the kubelet service on the joining node.
	KubeletArgs string `json:"kubelet_args"`
	// HostNameOverride is the host name the joining node will be known as in the MicroK8s cluster.
	HostNameOverride string `json:"hostname_override"`
	// DqliteVoterNodes is a list of known dqlite voter nodes. Each voter is identified as "$IP_ADDRESS:$PORT".
	// This is not included in the response when joining worker-only nodes.
	DqliteVoterNodes []string `json:"voters,omitempty"`
	// ServiceAccountKey is the private key used for signing ServiceAccount tokens.
	// This is not included in the response when joining worker-only nodes.
	ServiceAccountKey string `json:"service_account_key"`
	// AdminToken is a static token used to authenticate in the MicroK8s cluster as "admin".
	// This is not included in the response when joining worker-only nodes.
	AdminToken string `json:"admin_token,omitempty"`
	// CertificateAuthorityKey is the private key of the Certificate Authority.
	// Note that this is defined as *string, since the Python code expects this to be explicitly None/nil/null for worker only nodes.
	// This is not included in the response when joining worker-only nodes.
	CertificateAuthorityKey *string `json:"ca_key"`
	// DqliteClusterCertificate is the certificate for connecting to the Dqlite cluster.
	// This is not included in the response when joining worker-only nodes.
	DqliteClusterCertificate string `json:"cluster_cert,omitempty"`
	// DqliteClusterKey is the key for connecting to the Dqlite cluster.
	// This is not included in the response when joining worker-only nodes.
	DqliteClusterKey string `json:"cluster_key,omitempty"`
	// ControlPlaneNodes is a list of known control plane nodes running kube-apiserver.
	// This is only included in the response when joining worker-only nodes.
	ControlPlaneNodes []string `json:"control_plane_nodes"`
}

// Join implements "POST v2/join".
func Join(ctx context.Context, req JoinRequest) (*JoinResponse, error) {
	if !util.IsValidClusterToken(req.ClusterToken) {
		return nil, fmt.Errorf("invalid cluster token")
	}
	if err := util.RemoveClusterToken(req.ClusterToken); err != nil {
		return nil, fmt.Errorf("failed to remove cluster token: %w", err)
	}
	if !util.HasDqliteLock() {
		return nil, fmt.Errorf("failed to join the cluster: this is not an HA MicroK8s cluster")
	}

	// Sanity check cluster agent ports.
	clusterAgentBind := util.GetServiceArgument("cluster-agent", "--bind")
	_, port, _ := net.SplitHostPort(clusterAgentBind)
	if port != req.ClusterAgentPort {
		return nil, fmt.Errorf("cluster agent port needs to be set to %s", port)
	}

	// Sanity check node is not in cluster already.
	hostname := util.GetRemoteHost(req.RemoteHostName, req.RemoteAddress)
	dqliteCluster, err := util.GetDqliteCluster()
	if err != nil {
		return nil, fmt.Errorf("failed to retrieve dqlite cluster nodes: %w", err)
	}
	for _, node := range dqliteCluster {
		if strings.HasPrefix(node.Address, hostname+":") {
			return nil, fmt.Errorf("joining node %q is already known to dqlite", hostname)
		}
	}

	// Update dqlite cluster if needed
	if len(dqliteCluster) == 1 && strings.HasPrefix(dqliteCluster[0].Address, "127.0.0.1:") {
		requestHost, _, _ := net.SplitHostPort(req.HostPort)
		if err := util.UpdateDqliteIP(ctx, requestHost); err != nil {
			return nil, fmt.Errorf("failed to update dqlite address to %q: %w", requestHost, err)
		}

		// Wait for dqlite cluster to come up with new address
		dqliteCluster, err = util.WaitForDqliteCluster(ctx, func(c util.DqliteCluster) (bool, error) {
			return len(c) >= 1 && !strings.HasPrefix(c[0].Address, "127.0.0.1:"), nil
		})
		if err != nil {
			return nil, fmt.Errorf("failed waiting for dqlite cluster to come up: %w", err)
		}
	}

	callbackToken, err := util.GetOrCreateSelfCallbackToken()
	if err != nil {
		return nil, fmt.Errorf("could not retrieve self callback token: %w", err)
	}

	ca, err := util.ReadFile(util.SnapDataPath("certs", "ca.crt"))
	if err != nil {
		return nil, fmt.Errorf("failed reading cluster CA: %w", err)
	}
	kubeletArgs, err := util.ReadFile(util.SnapDataPath("args", "kubelet"))
	if err != nil {
		return nil, fmt.Errorf("failed to read arguments of kubelet service: %w", err)
	}
	if hostname != req.RemoteHostName {
		kubeletArgs = fmt.Sprintf("%s\n--hostname-override=%s", kubeletArgs, hostname)
	}

	if err := util.MaybePatchCalicoAutoDetectionMethod(ctx, hostname, true); err != nil {
		return nil, fmt.Errorf("failed to update cni configuration: %w", err)
	}

	if err := util.CreateNoCertsReissueLock(); err != nil {
		return nil, fmt.Errorf("failed to create lock file to disable certificate reissuing: %w", err)
	}
	response := &JoinResponse{
		CertificateAuthority: ca,
		CallbackToken:        callbackToken,
		APIServerPort:        util.GetServiceArgument("kube-apiserver", "--secure-port"),
		HostNameOverride:     hostname,
		KubeletArgs:          kubeletArgs,
	}

	if req.WorkerOnly {
		if err := util.AddCertificateRequestToken(fmt.Sprintf("%s-kubelet", req.ClusterToken)); err != nil {
			return nil, fmt.Errorf("failed adding certificate request token for kubelet: %w", err)
		}
		if err := util.AddCertificateRequestToken(fmt.Sprintf("%s-proxy", req.ClusterToken)); err != nil {
			return nil, fmt.Errorf("failed adding certificate request token for kube-proxy: %w", err)
		}

		// TODO: list of control plane nodes
		response.ControlPlaneNodes = []string{}
	} else {
		caKey, err := util.ReadFile(util.SnapDataPath("certs", "ca.key"))
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve cluster CA key: %w", err)
		}
		response.CertificateAuthorityKey = &caKey
		response.ServiceAccountKey, err = util.ReadFile(util.SnapDataPath("certs", "serviceaccount.key"))
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve service account key: %w", err)
		}
		response.AdminToken, err = util.GetKnownToken("admin")
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve token for admin user: %w", err)
		}
		response.DqliteClusterCertificate, err = util.ReadFile(util.SnapDataPath("var", "kubernetes", "backend", "cluster.crt"))
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve dqlite cluster certificate: %w", err)
		}
		response.DqliteClusterKey, err = util.ReadFile(util.SnapDataPath("var", "kubernetes", "backend", "cluster.key"))
		if err != nil {
			return nil, fmt.Errorf("failed to retrieve dqlite cluster key: %w", err)
		}
		voters := make([]string, 0, len(dqliteCluster))
		for _, node := range dqliteCluster {
			if node.NodeRole == 0 {
				voters = append(voters, node.Address)
			}
		}
		response.DqliteVoterNodes = voters
	}

	return response, nil
}
