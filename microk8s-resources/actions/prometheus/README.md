# Prometheus Operator

This is how we got the manifests:

```
git clone git@github.com:coreos/kube-prometheus.git
cp -r ./prometheus-operator/manifests/* $MICROK8S_HOME/microk8s-resources/actions/prometheus
```

Then update the deployments of prometheus and alertmanager to have one replica only.

There is no reason to automate this because this may not work in the future. This is not the recommended way of installing Prometheus Operator.


# References
 - https://github.com/coreos/kube-prometheus