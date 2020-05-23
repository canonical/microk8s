# Patch for dqlite

The patch to add the (dqlite)[https://github.com/canonical/dqlite]
is applied on top of the Kubernetes source code during the MicroK8s build process.

The dqlite patch is the file `build-scripts/patches/dqlite.patch`.

The dqlite patch is maintained in the (kubernetes-dqlite repository)[https://github.com/canonical/kubernetes-dqlite].
To produce it checkout the kubernetes-dqlite repository and head to the Kubernetes
branch you would like to build. For example:
```
git clone https://github.com/canonical/kubernetes-dqlite.git
cd kubernetes-dqlite/
git checkout release-1.18
```  
From `git log` note the commits related to dqlite. These commits are at the top.
Form the patch with for example:
```
git format-patch c3c94660a58998dde628de7c716a63b695327016^..f0cc11e7a398d9454e8c4d3a526d6372cf1a1889 --stdout > dqlite.patch
```

With the above the patch is produced against the release-1.18 HEAD.
This might not be what you actually need as you may want to create a patch against a
specific tag.
```
git reset c3c94660a58998dde628de7c716a63b695327016^  --soft 
git stash                                                    # put the patch on the stash
git reset 52c56ce7a8272c798dbc29846288d7cd9fbae032 --hard    # Go tho the 1.18.2 release commit
git stash apply
git commit -m "Apply the dqlite patch"
```

You can now proceed with the patch creation with `git format-patch`.

Remember to copy the `dqlite.patch` back to the `microk8s` source tree.
