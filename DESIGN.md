# DevSecOps Final Project — Design Decisions

_2026-11-06 · Zissi Heftler_

---

## Scope and Constraints

**Timeline:** 7 weeks × ~7 hrs = ~49 hrs total.

**Must ship (course grade):**
- A running app with its own Dockerfile
- Container image pushed to a registry from CI
- GitHub Actions pipeline
- Branches and pull requests on GitHub

**Nice-to-have (course):** Terraform IaC, Kubernetes, automated tests.

**Personal goals:** DevSecOps security gates that demonstrably catch problems; GitOps deployment via Argo CD; GitHub OIDC for AWS (no stored credentials); protected main branch with real PR review.

**Assumption:** ~6–8 hrs/week; built for learning and job skill growth, not production.

---

## Architecture Decisions

### ADR-0001 — EKS as Kubernetes platform

**Status:** Accepted  
**Context:** Kubernetes is a course nice-to-have; options include EKS (managed, industry-standard), k3s (lighter, cheaper), or GKE.  
**Decision:** AWS EKS via Terraform. One **t3.medium** node — t3.small cannot schedule Argo CD, the app, and the Kustomize controller simultaneously without hitting the pod scheduling limit. Cluster destroyed after every session to control cost.  
**Consequences:** ~$73/month control-plane cost + ~$33/month for t3.medium when running; mitigated by strict destroy habit. Terraform is more complex (~200–300 lines). Industry signal is high.

---

### ADR-0002 — Monorepo with app/ and deploy/ folders

**Status:** Accepted  
**Context:** GitOps needs a source of truth for Kubernetes manifests; could be same or separate repo.  
**Decision:** Single repo. App code lives in `app/`, Kubernetes manifests in `deploy/`. Argo CD watches `deploy/`.  
**Consequences:** Simpler auth, single PR history. CI must update `deploy/` without triggering the branch-protection review requirement — solved by a GitHub Actions bypass rule.

---

### ADR-0003 — GitHub Flow as branching model

**Status:** Accepted  
**Context:** Need a model that demonstrates protected main, PRs, and review without GitFlow's overhead.  
**Decision:** All work on feature branches; PRs into main; CI runs on merge. Main is always deployable.  
**Consequences:** Simple to operate solo. Second GitHub account provides required PR approval.

---

### ADR-0004 — Security gate philosophy: block on critical + secrets only

**Status:** Accepted  
**Context:** Gates that fire too often get bypassed; gates that never fire are invisible.  
**Decision:** Block merges on: secrets detected anywhere in the diff, critical CVEs in the container image, **high-severity** Bandit findings (`bandit -l -i`, level HIGH). Report medium/high CVEs and medium Bandit findings as PR annotations. Suppress informational findings.  
**Consequences:** Pipeline stays meaningful. Bandit HIGH catches the string-concatenation SQL pattern used in the demo branch. Demo story: plant a secret or add a vulnerable dep, show block, fix it, show pass.

---

### ADR-0005 — Cut kube-prometheus-stack

**Status:** Accepted  
**Context:** kube-prometheus-stack installs ~40 resources, costs 4–6 hrs to wire correctly, and was a stretch goal.  
**Decision:** No kube-prometheus-stack. Replace with: `kubectl top` for resource usage, an **AWS Budgets alert** (not a CloudWatch alarm) set up in week 1 before any AWS spend, and Argo CD sync status as the deployment health view. AWS Budgets requires no CloudWatch setup; it fires on actual or forecasted spend.  
**Consequences:** Monitoring story is simpler but coherent. Saves 4–6 hours for higher-priority items. AWS Budgets alert is added to the never-cut list. Can revisit kube-prometheus-stack in week 7 if ahead of schedule.

---

### ADR-0006 — App: FastAPI + SQLite with one intentional vulnerability

**Status:** Accepted  
**Context:** App must demonstrate security scanning but must not keep a known vulnerability permanently on the main branch.  
**Decision:** Python FastAPI, SQLite backend, `/health` + `/items` CRUD (GET + POST). No permanent vulnerability on main. The SQL injection demo lives on a long-lived branch `demo/bandit-finding` — a PR from that branch to main is used as the live demo for Act 3 (Bandit HIGH blocks the merge). The branch is never merged.  
**Consequences:** Main is always clean. The demo branch gives a live CI block to show without a known bad pattern in production history. The branch protection rule (Bandit HIGH gate) will itself block the merge, making the demo self-documenting.

---

### ADR-0007 — GitHub App on ruleset bypass list for image tag commits

**Status:** Accepted  
**Context:** CI must commit an updated image tag to `deploy/` after a build. Main is protected by a branch **ruleset** that requires PR review. The built-in `GITHUB_TOKEN` bypass does not reliably work with rulesets the same way it does with legacy branch protection rules.  
**Decision:** Create a GitHub App installed on the repo. Register the app's identity in the branch ruleset bypass list. CI uses `actions/create-github-app-token` to mint a short-lived installation token and commits the image tag update with it. `ci.yml` sets `paths-ignore: ['deploy/**']` so the tag commit does not re-trigger another CI run, preventing an infinite loop.  
**Consequences:** App identity is explicit and auditable in the bypass list. `paths-ignore: ['deploy/**']` on `ci.yml` is mandatory — without it every tag commit starts another build. Using a GitHub App token is the correct approach for ruleset bypass.

---

### ADR-0008 — Terraform `helm_release` for Argo CD bootstrap

**Status:** Accepted  
**Context:** EKS cluster is recreated each session; Argo CD must be re-installed every time without manual steps.  
**Decision:** Argo CD is installed via a Terraform `helm_release` resource inside `infra/cluster/`. The Argo CD `Application` CRD is applied by a `kubectl_manifest` resource in the same module. `terraform apply` leaves the cluster fully configured.  
**Consequences:** Cluster recreation is a single command. Argo CD version and config are version-controlled in Terraform. Terraform now couples infra provisioning and GitOps engine install — acceptable for a solo project.

---

### ADR-0009 — PR-based production promotion; `git revert` rollback

**Status:** Accepted  
**Context:** Need a promotion path from staging to production and a rollback mechanism that fits a GitOps model.  
**Decision:** Promote by opening a PR that updates `deploy/overlays/production/kustomization.yaml` to the new image tag; second-account reviewer approves; merge triggers Argo CD auto-sync. Roll back by running `git revert` on the image tag commit; Argo CD syncs the previous tag automatically.  
**Consequences:** Every production change has a PR, a review, and a full audit trail. Rollback is a commit, not an imperative command. Argo CD UI "rollback" button also available as a demo shortcut.

---

### ADR-0010 — Five-tool DevSecOps security stack

**Status:** Accepted  
**Context:** Need security checks covering code, dependencies, secrets, container images, and IaC — without overloading the pipeline.  
**Decision:** Bandit (Python SAST — block on HIGH), pip-audit (SCA — block on critical CVE), Gitleaks (secrets — block on any), **Trivy (container CVEs — block on critical, runs in `ci.yml` after `docker build`, pre-merge so the PR cannot merge if a critical CVE is found)**, Checkov (Terraform + Dockerfile IaC). Plus GitHub secret scanning + push protection and Dependabot. The image is built in CI for scanning but only pushed to ECR in `cd.yml` after merge.  
**Consequences:** Trivy pre-merge prevents a vulnerable image from ever reaching ECR. Each tool has a single clear job. All five have maintained GitHub Actions integrations.

---

### ADR-0011 — S3 remote state with two Terraform modules

**Status:** Accepted  
**Context:** EKS cluster is destroyed after each session; some AWS resources (ECR, IAM roles, state bucket) must persist. State locking is needed to prevent concurrent applies.  
**Decision:** Split into `infra/bootstrap/` (run once: S3 state bucket, ECR, IAM OIDC) and `infra/cluster/` (run each session: EKS, node group, Argo CD). S3 backend uses `use_lockfile = true` (Terraform ≥ 1.10) for state locking — no DynamoDB table needed. `make bootstrap` / `make up` / `make down` as the three lifecycle commands.  
**Consequences:** ECR images and IAM roles survive cluster recreation. Bootstrap is simpler — no DynamoDB table to provision or manage. `use_lockfile` stores a `.tflock` file alongside the state in S3. Requires Terraform ≥ 1.10.

---

### ADR-0012 — ClusterIP with port-forward; make down teardown order

**Status:** Accepted  
**Context:** Need external access to the app service for demos. LoadBalancer creates an AWS ELB (~$18/month when running and may leave dangling resources after destroy). NodePort is fragile. ClusterIP is cluster-internal unless port-forwarded.  
**Decision:** Kubernetes Service type is ClusterIP. Demo access via `kubectl port-forward svc/items-api 8080:80`. `make down` runs in two steps: (1) `kubectl delete application -n argocd --all` to remove Argo CD applications, then (2) `terraform destroy`. Step 1 prevents Argo CD finalizers from blocking Terraform and avoids leaving an orphaned ELB or dangling resources.  
**Consequences:** No ELB charges ($18/month avoided). Two-step `make down` is mandatory — skipping step 1 causes `terraform destroy` to hang on finalizers or leave dangling AWS resources.

---

### ADR-0013 — Container hardening defaults

**Status:** Accepted  
**Context:** Checkov flags Dockerfile security misconfigs as critical findings. Trivy finds more CVEs in full Python images than in slim ones. Hardening from day one avoids rework.  
**Decision:** `python:3.12-slim` base image. Non-root user: `RUN useradd --no-create-home appuser` and `USER appuser`. `COPY --chown=appuser:appuser` for source files. Single pinned `RUN pip install --no-cache-dir -r requirements.txt`. `EXPOSE` only the app port. No `apt-get` unless strictly needed.  
**Consequences:** Checkov passes without critical Dockerfile findings from week 1. Trivy finds fewer OS-level CVEs. Container cannot escalate to root. These choices should be reviewed in the first PR.

---

### ADR-0014 — OIDC trust rule scoping (GitHub → AWS)

**Status:** Accepted  
**Context:** An overly broad IAM trust policy can allow any GitHub repository — or any ref within the project repo — to assume the role. Minimal-privilege OIDC matters as much as no stored credentials.  
**Decision:** Two IAM roles with separate least-privilege policies. CI role: `ecr:GetAuthorizationToken` + `ecr:BatchGetImage` only, trusted on `repo:<owner>/<repo>:pull_request`. CD role: ECR write + `eks:DescribeCluster` + `eks:AccessKubernetesApi`, trusted on `repo:<owner>/<repo>:ref:refs/heads/main`. Both use `StringLike` on `token.actions.githubusercontent.com:sub`.  
**Consequences:** A PR-time workflow cannot push images. A CD-time workflow cannot run on a PR. Any drift in the trust policy is flagged by Checkov. The two-role structure should be established in `infra/bootstrap/` from week 1.

---

## Glossary

| Term | Definition |
|------|------------|
| Argo CD | A Kubernetes-native GitOps controller. Watches a Git repo and syncs the cluster to match it. |
| AWS Budgets | AWS service that sends email or SNS alerts when actual or forecasted spend crosses a threshold. No CloudWatch setup required. |
| Bandit | Python SAST tool. Flags insecure coding patterns; `-l -i` flags HIGH-severity issues including SQL string concatenation. |
| Branch protection | A GitHub setting (or ruleset) requiring CI checks and PR approval before code merges to main. |
| Checkov | Static analysis tool for Terraform and Dockerfile misconfigs. Runs in CI on IaC changes. |
| CVE | Common Vulnerabilities and Exposures. A public registry of known security vulnerabilities, each with a severity rating. |
| Dependabot | GitHub bot that opens automatic PRs when a dependency has a known CVE. |
| EKS | Amazon Elastic Kubernetes Service. AWS runs the Kubernetes control plane; you run the nodes. |
| GitHub App | A first-party GitHub OAuth application installed on a repo. Can be granted fine-grained permissions and added to branch ruleset bypass lists. |
| GitHub Flow | Branching model: feature branch → PR review → merge to main. Main is always deployable. |
| GitOps | Git is the single source of truth. Changes are commits; a controller syncs the cluster to match. |
| Gitleaks | Scans git history and diffs for secrets — tokens, passwords, keys. Blocks the PR if found. |
| Helm chart | A packaged Kubernetes application. Installed with the Helm CLI or Terraform's `helm_release` resource. |
| Kustomize | Kubernetes config tool that layers environment-specific patches (overlays) on shared base manifests. No templating. |
| OIDC (GitHub–AWS) | Trust protocol. GitHub Actions proves its identity to AWS with a short-lived signed token. No stored credentials. |
| Overlay | A Kustomize directory that patches base manifests for one environment (staging, production). |
| pip-audit | Checks Python dependencies against the OSV vulnerability database. Finds CVEs in installed packages. |
| Remote state | Terraform state stored in S3 so any machine or CI runner can share it without overwriting each other. |
| Ruleset bypass list | A GitHub branch ruleset setting that lets specified actors (GitHub Apps, users) push to main without meeting the normal review or CI requirements. |
| SAST | Static Application Security Testing. Scanning source code for security bugs without running it. |
| SCA | Software Composition Analysis. Scanning third-party dependencies for known CVEs. |
| Security gate | A CI check that blocks a PR merge when it finds a critical issue (secrets, CVEs, high SAST findings). |
| TestClient | FastAPI's built-in HTTP test client. Lets tests call the API without starting a real server. |
| Trivy | All-in-one scanner for CVEs in container images, OS packages, and language dependencies. Runs pre-merge in ci.yml. |
| use_lockfile | An S3 backend option in Terraform ≥ 1.10. Stores a `.tflock` file in S3 to serialize applies — replaces DynamoDB. |

---

## Risks and Optional Cuts

**Risk 1 — Week 3 EKS Terraform (high).** EKS nodes frequently need IAM, security group, or CNI debugging on first setup. This is the most likely source of schedule slip. Mitigate: start the week early; use the community `terraform-aws-modules/eks` module to reduce boilerplate; allow it to spill one day into week 4 before triggering the cut list.

**Risk 2 — Cost overrun (medium).** The EKS control plane charges ~$73/month whether or not workloads are running. A forgotten `make down` turns into a surprise bill. Mitigate: `make down` after every session, **AWS Budgets alert at $30** (set in week 1, on the never-cut list), check the AWS Cost Explorer dashboard at the start of each session.

**Risk 3 — Pipeline complexity (medium).** Nine moving parts connect in sequence: GitHub OIDC → ECR → EKS → Argo CD → Kustomize → five security tools. A failure anywhere stops the whole chain. Mitigate: get each layer working end-to-end before adding the next. Never wire two new layers in the same session.

**Risk 4 — Demo branch accidentally merged (low).** The SQL injection endpoint lives on `demo/bandit-finding` and must never reach main. Mitigate: the Bandit HIGH gate will block the merge automatically — which is also the demo itself. Add a note in the README explaining the branch's purpose so a reviewer does not dismiss the finding.

---

**Cut order if behind (drop from top first):**

1. Production namespace + promotion flow — keep staging only; course does not require two environments
2. Checkov — security story holds with four tools; Trivy + Gitleaks + Bandit + pip-audit still cover three layers
3. pytest-cov threshold — keep tests, drop the coverage gate enforcement; tests still run and block on failure
4. Kustomize overlays — use a flat `deploy/` manifest set; Argo CD GitOps story still works
5. **Nuclear: swap EKS for k3s on a t3.medium EC2** — only if week 3 is completely blocked; k3s is real Kubernetes, ~50 lines of Terraform, GitOps loop works identically

**Never cut:** app + Dockerfile + ECR push + GitHub Actions CI/CD + branch protection + PRs + at least Gitleaks as one working security gate + AWS Budgets alert.

---

**Optional items (revisit only in week 7 if ahead of schedule):**
- kube-prometheus-stack (cut in ADR-0005; would add monitoring depth)
- Argo CD Slack notifications (~1 hr; makes sync events visible in a channel)
- Kubernetes NetworkPolicy resources (adds real network security depth)
- SBOM generation with Syft + cosign image signing (~2 hrs; advanced supply-chain security)

---

## Final Summary

A Python FastAPI service (SQLite, two endpoints) deployed on AWS EKS via GitOps. Five security tools and two GitHub-native features (secret scanning + Dependabot) run in CI/CD; gates block on critical CVEs and high-severity code findings. All AWS access uses scoped GitHub OIDC — two separate IAM roles, CI read-only and CD write.

### Repository layout

```
repo/
├── app/
│   ├── main.py          # /health + /items CRUD
│   ├── requirements.txt
│   └── tests/           # pytest + TestClient
├── deploy/
│   ├── base/            # Kubernetes Deployment + ClusterIP Service
│   └── overlays/
│       ├── staging/     # image tag patch, namespace: staging
│       └── production/  # image tag patch, namespace: production
├── infra/
│   ├── bootstrap/       # S3 state (use_lockfile), ECR, IAM OIDC — run once
│   └── cluster/         # EKS, t3.medium node group, Argo CD helm_release — each session
├── .github/workflows/
│   ├── ci.yml           # on PR: lint + test + Bandit (HIGH) + pip-audit + Gitleaks + Checkov + docker build + Trivy
│   └── cd.yml           # on merge: ECR push (CD role) + tag update (GitHub App) + Argo CD auto-sync
├── Dockerfile           # python:3.12-slim, non-root user
├── Makefile             # make bootstrap / make up / make down (2-step teardown)
└── README.md
```

### CI/CD flow

**PR opened →** `ci.yml`: lint, test (pytest, 70% coverage), Bandit (HIGH), pip-audit, Gitleaks, Checkov, docker build + Trivy scan on local image (block on critical CVE). Second GitHub account approves. Merge.

**Push to main →** `cd.yml`: docker build + push to ECR (OIDC, CD role), `kustomize edit set image` updates `deploy/overlays/staging/`, commits to main (GitHub App token, ruleset bypass), Argo CD auto-syncs staging within seconds.

**Promote to production →** Manual PR updating `deploy/overlays/production/` image tag. Second account reviews. Merge. Argo CD auto-syncs prod.

**Rollback →** `git revert` the image tag commit. Push. Argo CD syncs the previous tag automatically.

### Security demo plan

| Act | What you plant | Tool that catches it | Gate result |
|-----|---------------|---------------------|-------------|
| 1 | AWS secret key in a file | Gitleaks + GitHub push protection | PR blocked |
| 2 | Known-CVE Python package | Trivy (post-push image scan) | CD pipeline blocked |
| 3 | String-concatenated SQL query | Bandit (pre-merge SAST) | Finding flagged; intentional, documented |

### All decisions

| Decision | What was chosen | ADR |
|----------|----------------|-----|
| App | FastAPI + SQLite, /health + /items; SQL injection demo on branch `demo/bandit-finding` only, never merged | ADR-0006 |
| Kubernetes | EKS, t3.medium node, Terraform-managed, destroy-after-session | ADR-0001 |
| Service exposure | ClusterIP; demo via `kubectl port-forward`; `make down` deletes Argo CD apps before `terraform destroy` | ADR-0012 |
| Repo structure | Monorepo: app/ + deploy/ | ADR-0002 |
| Branching | GitHub Flow; main protected via ruleset; second GitHub account as reviewer | ADR-0003 |
| Container | python:3.12-slim, non-root user, pinned deps, explicit EXPOSE | ADR-0013 |
| Auth (OIDC) | Two scoped IAM roles: CI (ECR read, on pull_request) + CD (ECR write + EKS, on main push) | ADR-0014 |
| IaC | Terraform; S3 backend with use_lockfile (≥ 1.10); bootstrap/ once + cluster/ each session | ADR-0011 |
| GitOps engine | Argo CD via Terraform helm_release; restored by terraform apply | ADR-0008 |
| Config | Kustomize overlays; staging auto-syncs; production promotes via PR | ADR-0009 |
| Security gates | Block on critical CVEs and high-severity Bandit findings; annotate medium | ADR-0004 |
| Security tools | Bandit (HIGH) + pip-audit + Gitleaks + Trivy (ci.yml, pre-merge) + Checkov + secret scanning + Dependabot | ADR-0010 |
| Image tag update | GitHub App on ruleset bypass list; paths-ignore: deploy/** on ci.yml prevents loop | ADR-0007 |
| Monitoring | kubectl top + AWS Budgets alert (week 1, never cut) + Argo CD UI | ADR-0005 |
| Tests | pytest + FastAPI TestClient + pytest-cov; 70% minimum enforced in CI | — |
| Image tag format | sha-$(git rev-parse --short HEAD) | — |
| VPC | AWS default VPC | — |

### Week-by-week schedule

| Week | Focus | Signal that it went wrong |
|------|-------|--------------------------|
| 1 | App + Dockerfile (hardened) + pytest + ci.yml: Gitleaks, Bandit (HIGH), pip-audit + AWS Budgets alert | App does not run in Docker; CI does not block a test secret |
| 2 | bootstrap/ Terraform (S3, ECR, IAM OIDC scoped roles) + cd.yml ECR push + Trivy added to ci.yml | Image not in ECR after a merged PR; Trivy not blocking a test CVE |
| 3 | cluster/ Terraform + make up / make down (2-step) + Checkov in ci.yml **(high risk)** | No working EKS cluster by end of week → trigger cut list |
| 4 | Kustomize overlays + Argo CD app (ClusterIP) + cd.yml GitOps loop + port-forward | Merge to main does not auto-sync staging |
| 5 | Three-act demo + production promotion PR + rollback demo + README | Demo cannot be recorded end-to-end |
| 6 | Polish + presentation prep | — |
| 7 | Buffer: fix slippage; if ahead, add monitoring stretch items | — |

### Cut order if behind

1. Production namespace + promotion flow
2. Checkov
3. pytest-cov threshold
4. Kustomize overlays
5. Nuclear: swap EKS for k3s on EC2

**Never cut:** app + Dockerfile + ECR push + GitHub Actions CI/CD + branch protection + PRs + at least Gitleaks + AWS Budgets alert.
