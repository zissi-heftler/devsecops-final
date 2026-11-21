# devsecops-final

DevSecOps final project — Python FastAPI service deployed on AWS EKS via GitOps.

## Stack

- **App**: FastAPI + SQLite (`/health`, `/items` CRUD, non-root container)
- **CI**: GitHub Actions — pytest (80% cov), Bandit HIGH, pip-audit, Gitleaks, Trivy, Checkov; image pushed to ECR on main
- **CD**: GitHub Actions — deploy-dev → e2e smoke tests → deploy-prod; Argo CD auto-syncs both environments
- **IaC**: Terraform — S3 remote state, ECR, IAM OIDC, EKS (t3.medium), Argo CD via Helm
- **GitOps**: Argo CD + Kustomize overlays (dev / production)
- **Auth**: GitHub OIDC → two scoped IAM roles (CI read-only ECR, CD ECR push + EKS)

---

## CI/CD flow

```
PR opened
  └── ci.yml: pytest · Bandit · pip-audit · Gitleaks · Trivy · Checkov
      (all gates must pass — build-push skipped on PRs)

Merged to main
  └── ci.yml: same gates + build-push to ECR (sha-<git-short-sha>)
      └── cd.yml (triggered on ci.yml success):
            deploy-dev:  kustomize edit set image → push overlay commit
                         → poll Argo CD until Synced at new commit
                         → kubectl rollout status (dev)
                         → e2e smoke tests via port-forward
            deploy-prod: (only if deploy-dev passes)
                         kustomize edit set image → push overlay commit
                         → Argo CD auto-syncs production
```

---

## Security demo

| Act | Branch | What is planted | Tool that catches it | Result |
|-----|--------|-----------------|----------------------|--------|
| 1 | `demo/gitleaks-finding` | Hardcoded AWS access key | Gitleaks | PR blocked |
| 2 | `demo/trivy-finding` | PyYAML 5.1 (CVE-2020-14343, Critical 9.8) | Trivy + pip-audit | PR blocked |
| 3 | `demo/bandit-finding` | String-concatenated SQL query | Bandit HIGH | PR blocked |

All three branches have open draft PRs with CI results showing the blocks. **None are ever merged.**

---

## Rollback

Argo CD tracks the git state of `deploy/overlays/`. To roll back either environment:

```bash
# Find the overlay commit to revert
git log --oneline deploy/overlays/production/

# Revert it — Argo CD syncs the previous image tag automatically
git revert <overlay-commit-sha>
git push origin main
```

No manual kubectl or Argo CD commands needed — the revert commit is the source of truth.

---

## Local dev

```bash
make dev        # run app with hot-reload (uvicorn)
make test       # pytest + 80% coverage gate (e2e tests excluded)
```

---

## Session ops

```bash
make bootstrap  # run once: S3 state bucket, ECR, IAM OIDC
make up         # each session: EKS cluster + Argo CD (10–15 min)
make kubeconfig # wire kubectl after make up
make down       # end of session: delete Argo CD apps, then terraform destroy

# If cluster was recreated mid-session and ECR tag already exists (immutable):
gh workflow run cd.yml --repo zissi-heftler/devsecops-final -f tag=sha-<sha>
```

---

## Repo layout

```
app/
  main.py               # FastAPI: /health + /items CRUD
  tests/test_api.py     # unit tests (TestClient, 80% coverage gate)
  tests/test_e2e.py     # smoke tests — run by cd.yml via port-forward (not in make test)
  pytest.ini            # excludes e2e marker from default pytest run
deploy/
  base/                 # Deployment + ClusterIP Service
  overlays/dev/         # image tag — updated by cd.yml on every main push
  overlays/production/  # image tag — promoted by cd.yml after e2e passes
infra/
  bootstrap/            # S3, ECR, IAM OIDC — run once per AWS account
  cluster/              # EKS, node group, Argo CD helm_release — run each session
.github/workflows/
  ci.yml                # PR + push: security gates + build-push (main only)
  cd.yml                # after CI on main: deploy-dev → e2e → deploy-prod
Dockerfile              # python:3.12-slim, non-root user
Makefile                # bootstrap / up / down / kubeconfig
DESIGN.md               # all architecture decisions (ADR-0001 – ADR-0014)
```

---

## Cost controls

- EKS cluster **destroyed after every session** (`make down`)
- AWS Budgets alert at **$30** — set up in week 1, never cut
- `make down` two-step: delete Argo CD apps first → `terraform destroy` (avoids finalizer hangs)
