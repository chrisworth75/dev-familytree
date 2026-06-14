# Deployment strategies — the three tiers

Three ways to run the *same* app, side by side, on purpose — to feel the trade-offs
between simple-local and prod-shaped. The golden rules that keep them from blurring:

1. **One spec, three renderings.** The app is described once by an **env-var contract**
   (`DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`, `SPRING_PROFILES_ACTIVE`, `PORT`,
   and React's `window.__ENV__`: `API_BASE`, `KEYCLOAK_*`, `TIER`). Compose and Helm
   just fill in those same variables. Same Dockerfiles feed all three tiers.
2. **Total isolation, encoded in the address.** The leading digit of every port *is*
   the tier. Tier 3 is the odd one out by form (hostnames, no ports).
3. **The app self-labels.** React shows a coloured **Tier badge** (`window.__ENV__.TIER`),
   so any open tab tells you which tier you're looking at.

## The map

| Tier | Host | Runtime | React | API | Keycloak | Postgres | Identity | Images |
|------|------|---------|-------|-----|----------|----------|----------|--------|
| **1 local** | Mac | Compose, by hand | `localhost:14202` | `:13200` | `:18081` | `:15432` | project `ft-t1` | `build:` (native) |
| **2 cd** | Calculon | Compose, Jenkins auto | `calculon:24202` | `:23200` | `:28081` | `:25432` | project `ft-t2` | `build:` (native) |
| **3 gitops** | Calculon | k3s + ArgoCD | `familytree.192.168.0.100.nip.io` | `api.familytree.…` | `keycloak.192.168.0.100.nip.io` | in-cluster PVC | ns `family-tree` | registry `192.168.0.186:5001` |

Badge colours: Tier 1 green, Tier 2 amber, Tier 3 blue.

## How each behaves
- **Tier 1 — `make t1-up`.** Push-by-hand. Build on the Mac, `up`, done. No registry,
  no cluster. Best for local dev and as a throwaway. Nothing watches anything.
- **Tier 2 — Jenkins (or `make t2-up`).** Jenkins polls `main` and runs
  `docker compose -p ft-t2 up -d --build` on Calculon → deploy-on-commit. Push-based
  "GitOps-lite": rollback = `git revert`; **no drift self-heal** (watches git, not the host).
- **Tier 3 — ArgoCD.** Pull-based: ArgoCD reconciles cluster-vs-git continuously and
  self-heals drift. Jenkins builds+pushes images and bumps the chart tag; ArgoCD deploys.

## Cheat sheet
```
make help     # all targets
make urls     # every tier's URLs
make t1-up    # Tier 1 on the Mac
make t2-up    # Tier 2 on Calculon (Jenkins normally does this)
make t3-apps  # Tier 3 ArgoCD app health
```

## Why these specific choices
- **Tiers 1 & 2 build images locally** (`build:`) → native arch, no registry. Only Tier 3
  pushes to the registry (and must build on Calculon — the Mac is arm64, Calculon amd64).
- **Tier 2 lives on Calculon** alongside Tier 3: different runtimes (Docker daemon vs k3s
  containerd) + the `2xxxx` port band + `ft-t2` naming keep them apart on one box.
- The whole ladder + rationale is in `journal/2026/June/14/notes.md`.
