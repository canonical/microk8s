package cmd

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/canonical/microk8s/cluster-agent/pkg/server"
	"github.com/canonical/microk8s/cluster-agent/pkg/util"
	utiltest "github.com/canonical/microk8s/cluster-agent/pkg/util/test"
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
		devMode, _ := cmd.Flags().GetBool("devmode")

		if devMode {
			log.Println("Running in development mode")
			util.SnapData = "data"
			util.CommandRunner = (&utiltest.MockRunner{Log: true}).Run
		}
		s := server.NewServer(time.Duration(timeout) * time.Second)
		log.Printf("Starting cluster agent on https://%s\n", bind)
		if err := http.ListenAndServeTLS(bind, cert, key, s); err != nil {
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
	rootCmd.Flags().Bool("devmode", false, "Turn on development mode (local data, mock commands)")
}
