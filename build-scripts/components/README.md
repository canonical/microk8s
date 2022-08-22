# Parts directory

This directory contains the build scripts for Go components built into MicroK8s.

The directory structure looks like this:

```
build-scripts/
    build-component.sh              <-- runs as `build-component.sh $component_name`
                                        - checks out the git repository
                                        - runs the `pre-patch.sh` script (if any)
                                        - applies the patches (if any)
                                        - runs the `build.sh` script to build the component
    component/
        $component_name/
            repository              <-- git repository to clone
            version.sh              <-- prints the repository tag or commit to checkout
            build.sh                <-- runs as `build.sh $output $version`
                                        first argument is the output directory where
                                        binaries should be placed, second is the component version
            pre-patch.sh            <-- runs as `pre-patch.sh`. takes any action needed before applying
                                        the component patches
            patches/
                ...                 <-- list of patches to apply after checkout (for stable versions)
            pre-patches/
                ...                 <-- list of patches to apply after checkout (for pre-releases)
            strict-patches/
                ...                 <-- list of patches to apply when building strictly confined snap
```
