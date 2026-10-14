---
name: strict-branch-maintenance
description: >-
  Use when the `strict` git branch needs to be updated with the latest
  changes from `master`, when a build on the `microk8s-strict` Launchpad
  recipe fails, or when the `latest/edge/strict` snap channel needs a fresh
  publish. Covers the branch's structure, how to rebase it safely, and how
  to trigger a republish.
---

# Maintaining the `strict` branch

## What this branch is for

`strict` is the git branch that Canonical's Launchpad snap recipe
[`microk8s-strict`](https://launchpad.net/~microk8s-dev/+snap/microk8s-strict)
builds from. It auto-builds and publishes to the snap store channel
`edge/strict` (i.e. `latest/edge/strict`) on every push. `snap/snapcraft.yaml`
on this branch declares `confinement: strict`, unlike `master` which stays
`classic`.

There is no other CI/CD path that publishes this channel — publishing is
entirely driven by pushes to this branch triggering a Launchpad build.

## Branch structure: "master + one commit"

`strict` is intentionally kept as **`master`'s history, plus exactly one
commit on top**, titled `Strict patch`. That single commit carries every
strict-confinement-specific change: `snap/snapcraft.yaml` confinement
plumbing, `snap/hooks/connect-plug-configuration` /
`disconnect-plug-configuration`, `microk8s-resources/connect-all-interfaces.sh`,
strict-specific CI env vars (`STRICT=yes`, `latest/edge/strict` channels) in
`.github/workflows/build-snap.yml`, docs, and any runc/`strict-patches`
adjustments needed only under strict confinement.

Do **not** let unrelated fixup commits pile up on top of `master` on this
branch. If you need to add or fix something strict-specific, squash it back
into the single `Strict patch` commit before pushing (see below). This keeps
`git diff origin/master origin/strict` a clean, reviewable single-purpose
diff, and makes every future rebase mechanical.

## When to update this branch

- Whenever `master` gets new commits you want the strict snap to include
  (routine maintenance, since the channel expires ~30 days after the last
  publish — see "Channel expiry" below).
- Whenever a `microk8s-strict` Launchpad build fails because `master`
  hasn't merged a fix yet (e.g. a new Kubernetes minor version's patches
  aren't merged, so `build-scripts/print-patches-for.py` falls back to an
  older, incompatible patch directory). In that case, get the relevant fix
  merged into `master` *first*, then rebase `strict` on top of it — don't
  patch around it directly on `strict`.

## How to rebase `strict` onto latest `master`

1. **Identify the current tip.** `git log --oneline -1 origin/strict` should
   show a single `Strict patch` commit sitting on top of some earlier
   `master` commit. Confirm this with:
   ```
   git merge-base --is-ancestor origin/master origin/strict  # should be false if master has moved
   git log --oneline origin/master..origin/strict            # should show exactly one commit: "Strict patch"
   ```
2. **Branch off the new `master` tip:**
   ```
   git checkout -b strict-rebase origin/master
   ```
3. **Cherry-pick the existing squashed `Strict patch` commit:**
   ```
   git cherry-pick -x <sha-of-current-Strict-patch-commit>
   ```
4. **Resolve conflicts by combining, not overriding.** Conflicts usually
   happen in shared files like `.github/workflows/build-snap.yml` when
   `master` has changed CI in the same region the strict patch touches
   (e.g. switching to a venv-based `pytest` invocation). Keep master's
   newer structure/tooling and layer the strict-specific env vars
   (`STRICT=yes`, `latest/edge/strict` channels, extra
   `connect-all-interfaces.sh` steps) on top of it — don't silently drop
   either side. Git's auto-merge in the same file often shows you the
   correct combined pattern to follow for the parts it *did* merge cleanly.
5. **If you added more than one commit** while resolving (e.g. an
   allow-empty marker commit for provenance, or a fixup), squash them back
   down to a single commit before finishing:
   ```
   git reset --soft origin/master
   git commit -s -m "Strict patch" -m "<body explaining what's included>"
   ```
6. **Sanity-check before pushing:**
   ```
   grep '^confinement:' snap/snapcraft.yaml   # must print "confinement: strict"
   git diff <previous-strict-tip> HEAD --stat # should show ONLY the expected
                                               # new master-side changes; nothing
                                               # from the strict patch should be
                                               # missing or duplicated
   ```
   If the update was prompted by a build failure involving
   `build-scripts/print-patches-for.py` (e.g. a Kubernetes/runc patch not
   applying), also verify the resolver now finds the right patch set, e.g.:
   ```
   python3 build-scripts/print-patches-for.py kubernetes v1.37.1
   ```
7. **Push.** This is a shared branch feeding a real, published snap
   channel — confirm with whoever asked for the update before force-pushing,
   then:
   ```
   git push origin strict-rebase:strict --force-with-lease=strict:<previous-strict-tip-sha>
   ```
   This triggers a fresh Launchpad build automatically.

## Verifying the publish

- Watch https://launchpad.net/~microk8s-dev/+snap/microk8s-strict for a new
  build (recent builds take ~15-20 minutes per architecture).
- Once built, confirm the channel actually updated:
  ```
  curl -s https://api.snapcraft.io/v2/snaps/info/microk8s \
    -H 'Snap-Device-Series: 16' | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print([c for c in d['channel-map'] if c['channel']['risk']=='edge' and c['channel']['branch']=='strict'])"
  ```

## Channel expiry (background: issue #412)

`latest/edge/strict` is a snap store *branch* channel (track=`latest`,
risk=`edge`, branch=`strict`), not a proper track. Branch channels expire
automatically after roughly 30 days without a new release, after which
`snap install --channel=latest/edge/strict` silently falls back to whatever
`latest/edge` revision exists instead of erroring — which can mask real
bugs in CI (a classic-confinement revision gets installed and tested while
assertions still expect strict-mode behavior). If this branch goes quiet for
a while, expect the channel to need a rebuild even with no code changes.
Compare with `1.36-strict`, which is a real non-expiring track — if this
keeps recurring, consider proposing an equivalent non-expiring track for
`master`-tracked builds instead of relying on the branch channel.
