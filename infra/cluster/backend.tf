# Remote state — S3 bucket created by infra/bootstrap/.
# Run `terraform output tf_state_bucket` in bootstrap/ to get the bucket name,
# then fill in the values below before running `make up`.
#
# use_lockfile = true (Terraform ≥ 1.10) replaces DynamoDB for state locking.
# ADR-0011.

terraform {
  backend "s3" {
    bucket       = "devsecops-final-tf-state"   # from bootstrap output
    key          = "cluster/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}
