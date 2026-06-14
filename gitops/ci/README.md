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

## Status

- **Build & Push image — ACTIVE.** Every build pushes `:$GIT_SHA` + `:latest` to the
  registry. (The old `when { branch 'main' }` guard was removed — it never matched in
  single-branch SCM jobs, silently skipping CD.)
- **Deploy (commit-back) — wired, gated on a credential.** Skips gracefully if
  `github-token` is absent (logs how to enable it); the build stays green.

## Already configured
1. **Build on Calculon, not the Mac.** Calculon is **x86_64**; the Mac is arm64.
   Jenkins runs on Calculon, so its `docker build` is native amd64. (Never push
   Mac-built images here — they crash with `exec format error` on the cluster.)
2. **Insecure registry on the Calculon Docker daemon**: `/etc/docker/daemon.json` →
   `{"insecure-registries": ["192.168.0.186:5001"]}`.
3. **Loop guard** — both jobs' Git SCM has a `UserExclusion` for committer
   `Calculon Jenkins`, so the deploy commit-back won't re-trigger builds.

## The one remaining step to close the loop
- **Add a `github-token` credential** in Jenkins (Manage Jenkins → Credentials):
  username/password kind, ID `github-token`, a GitHub PAT with push rights to
  `chrisworth75/dev-familytree`. Once present, the Deploy stage bumps the chart's
  `image.tag` to the build SHA, commits `[skip ci]`, and pushes — ArgoCD then
  redeploys tier 3 from git. (The loop guard above stops it re-triggering.)

## Notes
- The skeleton charts default to `image.tag: latest` (+ `pullPolicy: Always`).
  The first SHA bump from CI flips them to immutable SHA tags — the GitOps-proper
  end state (a git diff per deploy, trivially revertible).
- ArgoCD watches `main`; no webhook required (default 3-min poll), though an
  ArgoCD webhook from GitHub makes redeploys near-instant.
