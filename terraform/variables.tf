variable "kubeconfig_path" {
  description = "Path to the kubeconfig for the Calculon k3s cluster (server rewritten to 192.168.0.100:6443)"
  type        = string
  default     = "./kubeconfig"
}

variable "argocd_namespace" {
  description = "Namespace ArgoCD is installed into"
  type        = string
  default     = "argocd"
}

variable "argocd_chart_version" {
  description = "argo-cd Helm chart version (argoproj/argo-helm)"
  type        = string
  default     = "7.7.0"
}
