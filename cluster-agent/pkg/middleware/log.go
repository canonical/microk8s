package middleware

import (
	"log"
	"net/http"
	"time"
)

type responseWriter struct {
	http.ResponseWriter

	status int
	size   int
}

func (w *responseWriter) Write(b []byte) (int, error) {
	w.size += len(b)
	return w.ResponseWriter.Write(b)
}

func (w *responseWriter) WriteHeader(status int) {
	w.status = status
	w.ResponseWriter.WriteHeader(status)
}

// Log is a middleware function that logs all incoming HTTP requests.
func Log(next http.HandlerFunc) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		wrapped := &responseWriter{ResponseWriter: w}
		start := time.Now()
		next.ServeHTTP(wrapped, req)
		log.Printf("%s %d %q %d bytes in %v\n", req.Method, wrapped.status, req.RequestURI, wrapped.size, time.Since(start))
	})
}
