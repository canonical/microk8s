# Parts directory

This directory contains the build scripts for Go components built into MicroK8s.

The directory structure looks like this:

```
build-scripts/
    build-component.sh              <-- runs as `build-component.sh $component_name`
                                        checks out the git repository, applies the specified
                                        patches, then runs the `build.sh` step for the component
    component/
        $component_name/
            repository              <-- git repository to clone
            version.sh              <-- prints the repository tag or commit to checkout
            build.sh                <-- runs as `build.sh $output $version`
                                        first argument is the output directory where
                                        binaries should be placed, second is the component version
            patches/
                ...                 <-- list of patches to apply after checkout (for stable versions)
            pre-patches/
                ...                 <-- list of patches to apply after checkout (for pre-releases)
            strict-patches/
                ...                 <-- list of patches to apply when building strictly confined snap
```
