# devsecops-final

DevSecOps final project — Python FastAPI service deployed on AWS EKS via GitOps.

## Stack

- **App**: FastAPI + SQLite (`/health`, `/items` CRUD)
- **Container**: `python:3.12-slim`, non-root user
- **CI/CD**: GitHub Actions (`ci.yml` on PR, `cd.yml` on merge)
- **IaC**: Terraform (S3 state, ECR, EKS, Argo CD)
- **GitOps**: Argo CD + Kustomize overlays (staging / production)
- **Security gates**: Bandit (HIGH) · pip-audit · Gitleaks · Trivy · Checkov

## Security demo

| Act | What is planted | Tool that catches it | Result |
|-----|-----------------|----------------------|--------|
| 1 | AWS secret key in a file | Gitleaks + GitHub push protection | PR blocked |
| 2 | Known-CVE Python package | Trivy (pre-merge image scan) | PR blocked |
| 3 | String-concatenated SQL query | Bandit HIGH (pre-merge SAST) | PR blocked |

> Act 3 lives on branch `demo/bandit-finding` — that PR is never merged.

## Local dev

```bash
make dev        # run app with hot-reload
make test       # pytest + 70% coverage gate
```

## Repo layout

```
app/                    # FastAPI source + tests
deploy/base/            # Kubernetes Deployment + ClusterIP Service
deploy/overlays/        # staging + production Kustomize overlays
infra/bootstrap/        # S3 state bucket, ECR, IAM OIDC — run once
infra/cluster/          # EKS + node group + Argo CD — run each session
.github/workflows/
  ci.yml                # on PR: lint, test, Bandit, pip-audit, Gitleaks, Trivy, Checkov
  cd.yml                # on merge: ECR push + image tag update + Argo CD auto-sync
Dockerfile
Makefile                # make bootstrap / make up / make down
```

## Cost controls

- EKS cluster is **destroyed after every session** (`make down`)
- AWS Budgets alert set at **$30** — fires before real damage
- `make down` runs in two steps: delete Argo CD apps first, then `terraform destroy`
