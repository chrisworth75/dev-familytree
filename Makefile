# Family-tree deploy tiers — one entrypoint so the three strategies never blur.
# See DEPLOYMENT-STRATEGIES.md for the full map. Verbs are consistent per tier:
#   t1-* = Tier 1 (Compose, Mac, by hand)    ports 1xxxx
#   t2-* = Tier 2 (Compose, Calculon, CI)     ports 2xxxx
#   t3-* = Tier 3 (k3s + ArgoCD, Calculon)    *.192.168.0.100.nip.io
.DEFAULT_GOAL := help

T1   := docker compose -p ft-t1 -f deploy/tier1-local/compose.yml
T2_SSH := ssh calculon
T2_DIR := /opt/ft-t2
KUBECONFIG := terraform/kubeconfig
KC := KUBECONFIG=$(KUBECONFIG) kubectl -n family-tree
ARGO := KUBECONFIG=$(KUBECONFIG) kubectl -n argocd

## ----- Tier 1 : Compose on the Mac -------------------------------------------
.PHONY: t1-up t1-down t1-nuke t1-ps t1-logs t1-seed
t1-up: ## Tier 1: build + start the stack on the Mac
	$(T1) up -d --build
t1-down: ## Tier 1: stop (keep the DB volume)
	$(T1) down
t1-nuke: ## Tier 1: stop + delete the DB volume (fresh next up)
	$(T1) down -v
t1-ps: ## Tier 1: container status
	$(T1) ps
t1-logs: ## Tier 1: follow logs
	$(T1) logs -f --tail=50
t1-seed: ## Tier 1: re-run the seed (idempotent)
	$(T1) run --rm seed

## ----- Tier 2 : Compose on Calculon (Jenkins normally drives this) -----------
.PHONY: t2-up t2-down t2-ps t2-logs
t2-up: ## Tier 2: pull + build + start on Calculon (what Jenkins does)
	$(T2_SSH) 'cd $(T2_DIR) && git pull -q && docker compose -p ft-t2 -f deploy/tier2-cd/compose.yml up -d --build'
t2-down: ## Tier 2: stop on Calculon
	$(T2_SSH) 'cd $(T2_DIR) && docker compose -p ft-t2 -f deploy/tier2-cd/compose.yml down'
t2-ps: ## Tier 2: container status on Calculon
	$(T2_SSH) 'docker compose -p ft-t2 ps'
t2-logs: ## Tier 2: logs on Calculon
	$(T2_SSH) 'cd $(T2_DIR) && docker compose -p ft-t2 -f deploy/tier2-cd/compose.yml logs --tail=50'

## ----- Tier 3 : k3s + ArgoCD on Calculon ------------------------------------
.PHONY: t3-pods t3-apps t3-sync t3-seed
t3-pods: ## Tier 3: pods in the family-tree namespace
	$(KC) get pods
t3-apps: ## Tier 3: ArgoCD application sync/health
	$(ARGO) get applications
t3-sync: ## Tier 3: force ArgoCD to refresh from git
	$(ARGO) annotate app family-tree-root argocd.argoproj.io/refresh=hard --overwrite
t3-seed: ## Tier 3: re-run the seed job
	$(KC) delete job seed --ignore-not-found && \
	helm template api gitops/charts/api --show-only templates/seed-job.yaml | $(KC) apply -f -
t3-argocd: ## Tier 3: ArgoCD UI URL + admin password
	@echo "http://argocd.192.168.0.100.nip.io  (user: admin)"
	@echo -n "password: "; KUBECONFIG=$(KUBECONFIG) kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo

## ----- Cross-tier ------------------------------------------------------------
.PHONY: urls help
urls: ## Print every tier's URLs
	@echo "Tier 1 (Mac):       http://localhost:14202  api http://localhost:13200  kc http://localhost:18081"
	@echo "Tier 2 (Calculon):  http://calculon:24202    api http://calculon:23200   kc http://calculon:28081"
	@echo "Tier 3 (gitops):    http://familytree.192.168.0.100.nip.io  api http://api.familytree.192.168.0.100.nip.io"
	@echo "ArgoCD UI:          http://argocd.192.168.0.100.nip.io  (admin; 'make t3-argocd' for password)"

help: ## This help
	@grep -hE '^[a-z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*##"}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
