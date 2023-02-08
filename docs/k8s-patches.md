# Patches for Kubernetes
 
The patch to add kubelite is applied on top of the Kubernetes source code during
the MicroK8s build process.

The Kubernetes patches are under `build-scripts/patches/`.

The patches are maintained in the [kubernetes-dqlite repository](https://github.com/canonical/kubernetes-dqlite).
To produce them checkout the kubernetes-dqlite repository and head to the Kubernetes
branch you would like to build. For example:
```
git clone https://github.com/canonical/kubernetes-dqlite.git
cd kubernetes-dqlite/
git checkout release-1.18
```  
From `git log` note down the commits related to k8s patches. These commits are at the top.
Form the patch with for example:
```
git format-patch c3c94660a58998dde628de7c716a63b695327016^..f0cc11e7a398d9454e8c4d3a526d6372cf1a1889 --stdout > k8s.patch
```

Remember to copy the produced patch file back to the `microk8s` source tree.
