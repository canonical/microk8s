package server

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
)

// UnmarshalJSON unmarshals JSON data from the HTTP request body.
func UnmarshalJSON(r *http.Request, v interface{}) error {
	b, err := ioutil.ReadAll(r.Body)
	if err != nil {
		return fmt.Errorf("failed to read request body: %w", err)
	}
	return json.Unmarshal(b, v)
}

type httpError struct {
	Error string `json:"error"`
}

// HTTPError creates an HTTP response to handle errors.
func HTTPError(w http.ResponseWriter, status int, err error) {
	w.WriteHeader(status)
	HTTPResponse(w, &httpError{Error: err.Error()})
}

// HTTPResponse creates an HTTP response for successful calls.
func HTTPResponse(w http.ResponseWriter, v interface{}) {
	b, err := json.Marshal(v)
	if err == nil {
		w.Write(b)
	}
}
