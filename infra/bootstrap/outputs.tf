output "ecr_repository_url" {
  description = "Full ECR image URL (without tag) — use in cd.yml as the IMAGE variable"
  value       = aws_ecr_repository.app.repository_url
}

output "tf_state_bucket" {
  description = "S3 bucket name — paste into infra/cluster/backend.tf"
  value       = aws_s3_bucket.tf_state.id
}

output "ci_role_arn" {
  description = "IAM role ARN for ci.yml (read-only ECR, trusted on pull_request)"
  value       = aws_iam_role.ci.arn
}

output "cd_role_arn" {
  description = "IAM role ARN for cd.yml (ECR push + EKS, trusted on refs/heads/main)"
  value       = aws_iam_role.cd.arn
}
