package server

import (
	"fmt"
	"net/http"
	"time"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
	v2 "github.com/canonical/microk8s/cluster-agent/pkg/api/v2"
	"github.com/canonical/microk8s/cluster-agent/pkg/middleware"
)

const (
	ClusterApiV1 = "/cluster/api/v1.0"
	ClusterApiV2 = "/cluster/api/v2.0"
)

// NewServer creates a new *http.ServeMux and registers the MicroK8s cluster agent API endpoints.
func NewServer(timeout time.Duration) *http.ServeMux {
	server := http.NewServeMux()

	withMiddleware := func(f http.HandlerFunc) http.HandlerFunc {
		timeoutMiddleware := middleware.Timeout(timeout)
		return middleware.Log(timeoutMiddleware(f))
	}

	// POST /v1/join
	server.HandleFunc(fmt.Sprintf("%s/join", ClusterApiV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		req := v1.JoinRequest{}
		if err := UnmarshalJSON(r, &req); err != nil {
			HTTPError(w, http.StatusBadRequest, err)
			return
		}

		// Set remote address from request object.
		req.RemoteAddress = r.RemoteAddr

		resp, err := v1.Join(r.Context(), req)
		if err != nil {
			HTTPError(w, http.StatusInternalServerError, err)
			return
		}

		HTTPResponse(w, resp)
	}))

	// POST v1/sign-cert
	server.HandleFunc(fmt.Sprintf("%s/sign-cert", ClusterApiV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		req := v1.SignCertRequest{}
		if err := UnmarshalJSON(r, &req); err != nil {
			HTTPError(w, http.StatusBadRequest, err)
			return
		}

		resp, err := v1.SignCert(r.Context(), req)
		if err != nil {
			HTTPError(w, http.StatusInternalServerError, err)
			return
		}

		HTTPResponse(w, resp)
	}))

	// POST v1/configure
	server.HandleFunc(fmt.Sprintf("%s/configure", ClusterApiV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		req := v1.ConfigureRequest{}
		if err := UnmarshalJSON(r, &req); err != nil {
			HTTPError(w, http.StatusBadRequest, err)
			return
		}

		err := v1.Configure(r.Context(), req)
		if err != nil {
			HTTPError(w, http.StatusInternalServerError, err)
			return
		}
		HTTPResponse(w, map[string]string{"result": "ok"})
	}))

	// POST v1/upgrade
	server.HandleFunc(fmt.Sprintf("%s/upgrade", ClusterApiV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		req := v1.UpgradeRequest{}
		if err := UnmarshalJSON(r, &req); err != nil {
			HTTPError(w, http.StatusBadRequest, err)
			return
		}

		err := v1.Upgrade(r.Context(), req)
		if err != nil {
			HTTPError(w, http.StatusInternalServerError, err)
			return
		}
		HTTPResponse(w, map[string]string{"result": "ok"})
	}))

	// POST v2/join
	server.HandleFunc(fmt.Sprintf("%s/join", ClusterApiV2), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		req := v2.JoinRequest{}
		if err := UnmarshalJSON(r, &req); err != nil {
			HTTPError(w, http.StatusBadRequest, err)
			return
		}

		// This is required because the Python code will send either `false` or `"as-worker"`
		if req.Worker != nil {
			if v, ok := req.Worker.(bool); ok {
				req.WorkerOnly = v
			} else if s, ok := req.Worker.(string); ok {
				req.WorkerOnly = s == "as-worker"
			}
		}

		req.RemoteAddress = r.RemoteAddr
		req.HostPort = r.Host

		response, err := v2.Join(r.Context(), req)
		if err != nil {
			HTTPError(w, http.StatusInternalServerError, err)
			return
		}
		HTTPResponse(w, response)
	}))

	return server
}
