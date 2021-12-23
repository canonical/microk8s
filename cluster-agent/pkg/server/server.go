package server

import (
	"fmt"
	"net/http"
	"time"

	v1 "github.com/canonical/microk8s/cluster-agent/pkg/api/v1"
	"github.com/canonical/microk8s/cluster-agent/pkg/middleware"
)

const (
	ClusterApiV1 = "/cluster/api/1.0"
	ClusterApiV2 = "/cluster/api/2.0"
)

// NewServer creates a new *http.ServeMux and registers the MicroK8s cluster agent API endpoints.
func NewServer(timeout time.Duration) *http.ServeMux {
	server := http.NewServeMux()

	withMiddleware := func(f http.HandlerFunc) http.HandlerFunc {
		handler := middleware.Timeout(timeout)
		return handler(f)
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

	return server
}
