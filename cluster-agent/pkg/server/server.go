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
	// ClusterAPIV1 is the version 1 of the MicroK8s cluster API.
	ClusterAPIV1 = "/cluster/api/v1.0"
	// ClusterAPIV2 is the version 2 of the MicroK8s cluster API.
	ClusterAPIV2 = "/cluster/api/v2.0"
)

// NewServer creates a new *http.ServeMux and registers the MicroK8s cluster agent API endpoints.
func NewServer(timeout time.Duration) *http.ServeMux {
	server := http.NewServeMux()

	withMiddleware := func(f http.HandlerFunc) http.HandlerFunc {
		timeoutMiddleware := middleware.Timeout(timeout)
		return middleware.Log(timeoutMiddleware(f))
	}

	// Default handler
	server.HandleFunc("/", withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		HTTPError(w, http.StatusNotFound, fmt.Errorf("not found"))
	}))

	// POST /v1/join
	server.HandleFunc(fmt.Sprintf("%s/join", ClusterAPIV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
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
	server.HandleFunc(fmt.Sprintf("%s/sign-cert", ClusterAPIV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
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
	server.HandleFunc(fmt.Sprintf("%s/configure", ClusterAPIV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
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
	server.HandleFunc(fmt.Sprintf("%s/upgrade", ClusterAPIV1), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
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
	server.HandleFunc(fmt.Sprintf("%s/join", ClusterAPIV2), withMiddleware(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusNotFound)
			return
		}
		req := v2.JoinRequest{}
		if err := UnmarshalJSON(r, &req); err != nil {
			HTTPError(w, http.StatusBadRequest, err)
			return
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
