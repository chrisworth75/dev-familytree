# Terraform bootstrap — ArgoCD on Calculon k3s

Installs ArgoCD into the k3s cluster on Calculon and applies the app-of-apps root
Application. ArgoCD then reconciles the family-tree stack (postgres, keycloak, api,
react) from `gitops/` on the `main` branch.

## Prerequisites
- The k3s cluster is up on Calculon (see repo root plan).
- `kubectl` and `terraform` on the machine running this (the Mac).
- A kubeconfig for the cluster at `./kubeconfig` (server = `https://192.168.0.100:6443`):

  ```sh
  ssh calculon 'sed "s#https://127.0.0.1:6443#https://192.168.0.100:6443#" /etc/rancher/k3s/k3s.yaml' > kubeconfig
  ```

## Usage
```sh
terraform init
terraform apply
```

After apply, watch ArgoCD reconcile:
```sh
export KUBECONFIG=./kubeconfig
kubectl -n argocd get applications
kubectl -n family-tree get pods
```

State is local (skeleton). The DB password and namespaces are owned by the Helm
charts / ArgoCD, not Terraform.
