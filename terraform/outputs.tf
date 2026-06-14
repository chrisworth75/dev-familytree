output "argocd_namespace" {
  value = helm_release.argocd.namespace
}

output "argocd_admin_password_cmd" {
  description = "Command to read the initial ArgoCD admin password"
  value       = "KUBECONFIG=${var.kubeconfig_path} kubectl -n ${var.argocd_namespace} get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d"
}

output "ingress_urls" {
  value = {
    react    = "http://familytree.192.168.0.100.nip.io"
    api      = "http://api.familytree.192.168.0.100.nip.io"
    keycloak = "http://keycloak.192.168.0.100.nip.io"
    argocd   = "http://argocd.192.168.0.100.nip.io"
  }
}
