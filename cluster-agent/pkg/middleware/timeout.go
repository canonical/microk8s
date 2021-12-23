package middleware

import (
	"context"
	"net/http"
	"time"
)

// Timeout is a middleware function that adds a deadline to the request context.
func Timeout(d time.Duration) func(http.HandlerFunc) http.HandlerFunc {
	return func(next http.HandlerFunc) http.HandlerFunc {
		return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
			ctx, cancel := context.WithDeadline(req.Context(), time.Now().Add(d))
			defer cancel()

			next.ServeHTTP(w, req.WithContext(ctx))
		})
	}
}
