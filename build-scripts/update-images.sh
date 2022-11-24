#!/bin/bash -x

## Description:
#
# Install MicroK8s from a specific channel and update the list of images required by MicroK8s
# and the core addons.
#
## Example:
#
# $ ./build-scripts/update-images.sh latest/edge build-scripts/images.txt

sudo snap install microk8s --classic --channel $1
sudo microk8s status --wait-ready

sudo microk8s enable storage ingress metrics-server dns

sudo microk8s kubectl apply -f - <<EOF
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources: { requests: { storage: 5Gi } }
---
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  volumes:
    - name: pvc
      persistentVolumeClaim:
        claimName: my-pvc
  containers:
    - name: nginx
      image: nginx
      ports:
        - containerPort: 80
      volumeMounts:
        - name: pvc
          mountPath: /usr/share/nginx/html
EOF

while ! sudo microk8s kubectl wait --for=condition=ready pod/nginx; do
  sudo microk8s kubectl get pod,pvc -A
  sleep 3
done

while ! sudo microk8s kubectl wait -n kube-system --for=jsonpath='{.status.readyReplicas}=1' deploy/coredns; do
  echo 'waiting for dns'
  sleep 3
done

sudo microk8s ctr image ls -q | grep -v sha256 | grep -v nginx:latest | sort > $2
