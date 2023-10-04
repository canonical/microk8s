# Contributor Guide

MicroK8s is open source ([Apache License 2.0](./LICENSE)) and actively seeks any community contributions for code, add-ons, suggestions and documentation.
Many of the features currently part of MicroK8s originated in the community, and we are very keen for that to continue. This page details a few notes, 
workflows and suggestions for how to make contributions most effective and help us all build a better MicroK8s for everyone - please give them a read before
working on any contributions.

## Licensing

MicroK8s has been created under the [Apache License 2.0](./LICENSE), which will cover any contributions you may make to this project. Please familiarise
yourself with the terms of the license.

Additionally, MicroK8s uses the Harmony CLA agreement.  It’s the easiest way for you to give us permission to use your contributions. 
In effect, you’re giving us a licence, but you still own the copyright — so you retain the right to modify your code and use it in
other projects. Please [sign the CLA here](https://ubuntu.com/legal/contributors/agreement) before making any contributions.

## Code of conduct

MicroK8s has adopted the Ubuntu code of Conduct. You can read this in full [here](https://ubuntu.com/community/code-of-conduct).

## Contributing code

The workflow for contributing code is as follows:

1. **Create/choose an issue**: MicroK8s tracks issues at [https://github.com/canonical/microk8s/issues](https://github.com/canonical/microk8s/issues). If you
   want to work on a new feature, create an issue first! This gives everyone a place to discuss scope and implementation.
2. **Create a fork of the MicroK8s repo**
3. **Make a new branch for your contribution**. Write your code there.
4. For details on how to **build and test MicroK8s**, see the [build instructions](./docs/build.md). Add new tests as needed,
   and make sure the existing tests continue to pass when your changes are complete.
5. **Submit a pull request** to get changes from your branch into master. You can add "#Fixes xxx" where `xxx` is the issue number to 
   automatically link to the issue you chose or created earlier.
6. Someone will review your PR and may make suggestions or have comments, so **keep an eye on the PR status** in case there are changes to make
7. **Please make sure you have submitted your [CLA form](https://ubuntu.com/legal/contributors/agreement) if you are a first time contributor**.
8. Thanks!

## Documentation

Docs for MicroK8s are published online at [https://microk8s.io/docs](https://microk8s.io/docs). You can make suggestions and edit the pages themselves by joining 
the Kubernetes discourse at [discuss.kubernetes.io](https://discuss.kubernetes.io/t/introduction-to-microk8s/11243) or follow the link at
the bottom of any of the pages published at [https://microk8s.io/docs](https://microk8s.io/docs)
There is a documentation page which describes how to write and edit docs, [published as part of the documentation](https://microk8s.io/docs/docs).

