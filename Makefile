.PHONY: dev test bootstrap up down kubeconfig

dev:
	cd app && pip install -r requirements-dev.txt && uvicorn main:app --reload --port 8000

test:
	cd app && pytest --cov=. --cov-report=term-missing --cov-fail-under=70

bootstrap:
	cd infra/bootstrap && terraform init && terraform apply

up:
	cd infra/cluster && terraform init && terraform apply

# ADR-0012: two-step teardown — delete Argo CD apps first to avoid finalizer
# hangs, then destroy the cluster.  Skipping step 1 causes terraform destroy
# to block on finalizers or leave dangling AWS resources.
down:
	kubectl delete application -n argocd --all --ignore-not-found
	cd infra/cluster && terraform destroy

# Convenience: wire kubectl to the cluster after make up
kubeconfig:
	aws eks update-kubeconfig --region us-east-1 --name devsecops-final
