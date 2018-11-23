# Prometheus Operator

This is how we got the manifests:

```
git clone https://github.com/coreos/prometheus-operator.git
git checkout release-0.25
cp ./prometheus-operator/contrib/kube-prometheus/manifests $MICROK8S_HOME/microk8s-resources/prometheus
mkdir $MICROK8S_HOME/microk8s-resources/prometheus/resources/
mv $MICROK8S_HOME/microk8s-resources/prometheus/*CustomResourceDefinitions.yaml $MICROK8S_HOME/microk8s-resources/prometheus/resources/
```

Then update the deployments of prometheus and alertmanager to have one replica only.

There is no reason to automate this because this may not work in the future. This is not the recommended way of installing Prometheus Operator.


# References
 - https://github.com/coreos/prometheus-operator/tree/master/contrib/kube-prometheus