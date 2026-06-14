# Bootstrap only: install ArgoCD, then apply the app-of-apps root.
# ArgoCD's automated sync reconciles everything else from gitops/ in the repo.
# (The DB Secret and namespaces are owned by the Helm charts / ArgoCD, not here,
#  to keep a single owner per resource.)

resource "helm_release" "argocd" {
  name             = "argocd"
  repository       = "https://argoproj.github.io/argo-helm"
  chart            = "argo-cd"
  version          = var.argocd_chart_version
  namespace        = var.argocd_namespace
  create_namespace = true

  # Local skeleton: serve the API/UI over plain HTTP (no TLS in front of it).
  set {
    name  = "configs.params.server\\.insecure"
    value = "true"
  }
}

# App-of-apps bootstrap. The root Application lives in git too, but it must be
# applied once imperatively to kick off GitOps. Waits for the Application CRD
# (installed by the chart above) before applying.
resource "terraform_data" "root_app" {
  depends_on       = [helm_release.argocd]
  triggers_replace = filemd5("${path.module}/../gitops/argocd/root-app.yaml")

  provisioner "local-exec" {
    command = <<-EOT
      KUBECONFIG=${var.kubeconfig_path} sh -c '
        kubectl wait --for=condition=Established crd/applications.argoproj.io --timeout=120s &&
        kubectl apply -f ${path.module}/../gitops/argocd/root-app.yaml
      '
    EOT
  }
}

# Expose the ArgoCD UI via Traefik (http://argocd.192.168.0.100.nip.io).
resource "terraform_data" "argocd_ingress" {
  depends_on       = [helm_release.argocd]
  triggers_replace = filemd5("${path.module}/argocd-ingress.yaml")

  provisioner "local-exec" {
    command = "KUBECONFIG=${var.kubeconfig_path} kubectl apply -f ${path.module}/argocd-ingress.yaml"
  }
}
