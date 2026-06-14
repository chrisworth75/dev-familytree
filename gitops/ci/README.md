# CI → CD wiring (Jenkins → registry → ArgoCD)

The two Jenkinsfiles (`/Jenkinsfile` for the API, `/family-tree-react/Jenkinsfile`
for the SPA) each end with two `main`-only stages:

1. **Build & Push image** — `docker build` + push `:$GIT_SHA` and `:latest` to the
   Mac registry `192.168.0.186:5001`.
2. **Deploy (GitOps tag bump)** — `sed` the chart's top-level `image.tag` to
   `$GIT_SHA`, commit `ci(<svc>): deploy <sha> [skip ci]`, and push to `main`.
   ArgoCD (auto-sync) then rolls the new tag out to k3s.

So: **push to `main` → Jenkins builds/tests → image pushed → tag bumped in git →
ArgoCD redeploys.**

## Prerequisites to activate (one-time Jenkins/Calculon setup)

1. **Build on Calculon, not the Mac.** Calculon is **x86_64**; the Mac is arm64.
   Images must be amd64. Jenkins runs on Calculon, so its `docker build` is
   already native amd64 — good. (Never push Mac-built images here: they're arm64
   and crash with `exec format error` on the cluster.)

2. **Insecure registry on the Calculon Docker daemon** (for `docker push`):
   `/etc/docker/daemon.json` →
   `{"insecure-registries": ["192.168.0.186:5001"]}` then `systemctl restart docker`.
   (Already configured.)

3. **`github-token` credential** in Jenkins — a username/password (PAT) credential
   with push rights to `chrisworth75/dev-familytree`, used by the deploy stage's
   `git push`.

4. **Loop guard** so the deploy commit doesn't re-trigger the job. On each job's
   Git SCM config add behaviour **"Polling ignores commits from certain users"**
   = `Calculon Jenkins` (the deploy-commit author). The `[skip ci]` marker is
   belt-and-braces.

## Notes
- The skeleton charts default to `image.tag: latest` (+ `pullPolicy: Always`).
  The first SHA bump from CI flips them to immutable SHA tags — the GitOps-proper
  end state (a git diff per deploy, trivially revertible).
- ArgoCD watches `main`; no webhook required (default 3-min poll), though an
  ArgoCD webhook from GitHub makes redeploys near-instant.
