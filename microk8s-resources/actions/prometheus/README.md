# Prometheus Operator

This is how we got the manifests:

```
git clone https://github.com/coreos/prometheus-operator.git
cp -r ./prometheus-operator/manifests $MICROK8S_HOME/microk8s-resources/prometheus
```

Then update the deployments of prometheus and alertmanager to have one replica only.

There is no reason to automate this because this may not work in the future. This is not the recommended way of installing Prometheus Operator.


# References
 - https://github.com/coreos/prometheus-operator/tree/master/contrib/kube-prometheus