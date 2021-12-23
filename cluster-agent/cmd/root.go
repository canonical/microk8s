package cmd

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/canonical/microk8s/cluster-agent/pkg/middleware"
	"github.com/spf13/cobra"
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "cluster-agent",
	Short: "MicroK8s cluster agent",
	Long: `The MicroK8s cluster agent is an API server that orchestrates the
lifecycle of a MicroK8s cluster.`,
	Run: func(cmd *cobra.Command, args []string) {
		bind, _ := cmd.Flags().GetString("bind")
		key, _ := cmd.Flags().GetString("keyfile")
		cert, _ := cmd.Flags().GetString("certfile")
		timeout, _ := cmd.Flags().GetInt("timeout")

		handler := func(w http.ResponseWriter, req *http.Request) {
			w.Write([]byte(`{"result":"ok"}`))
		}

		withMiddleware := func(f http.HandlerFunc) http.HandlerFunc {
			m := middleware.Timeout(time.Duration(timeout) * time.Second)
			return m(f)
		}

		server := http.NewServeMux()
		server.HandleFunc("/cluster/api/1.0/test", withMiddleware(handler))

		log.Printf("Starting cluster agent on https://%s\n", bind)
		if err := http.ListenAndServeTLS(bind, cert, key, server); err != nil {
			log.Fatalf("Failed to listen: %s", err)
		}
	},
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() {
	err := rootCmd.Execute()
	if err != nil {
		os.Exit(1)
	}
}

func init() {
	rootCmd.Flags().String("bind", "0.0.0.0:25000", "Listen address for server")
	rootCmd.Flags().String("keyfile", "", "Private key for serving TLS")
	rootCmd.Flags().String("certfile", "", "Certificate for serving TLS")
	rootCmd.Flags().Int("timeout", 240, "Default request timeout (in seconds)")
}
