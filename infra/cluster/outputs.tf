output "cluster_name" {
  description = "EKS cluster name — use with 'aws eks update-kubeconfig --name <value>'"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_region" {
  description = "AWS region the cluster was created in"
  value       = var.aws_region
}
