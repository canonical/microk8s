package util_test

import "github.com/canonical/microk8s/cluster-agent/pkg/util"

func init() {
	util.Snap = "testdata"
	util.SnapData = "testdata"
}
