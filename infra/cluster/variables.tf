variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short project name used to prefix resource names"
  type        = string
  default     = "devsecops-final"
}

variable "node_instance_type" {
  description = "EC2 instance type for the EKS node group"
  type        = string
  default     = "t3.medium"   # ADR-0001: t3.small cannot schedule ArgoCD + app simultaneously
}

variable "cd_role_arn" {
  description = "ARN of the CD IAM role (output from infra/bootstrap) — granted EKS access-entry"
  type        = string
}
