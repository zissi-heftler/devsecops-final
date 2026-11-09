.PHONY: dev test bootstrap up down

dev:
	cd app && pip install -r requirements-dev.txt && uvicorn main:app --reload --port 8000

test:
	cd app && pytest --cov=. --cov-report=term-missing --cov-fail-under=70

bootstrap:
	cd infra/bootstrap && terraform init && terraform apply

# TODO week-3: up / down (EKS cluster lifecycle)
up:
	cd infra/cluster && terraform init && terraform apply

down:
	kubectl delete application -n argocd --all --ignore-not-found
	cd infra/cluster && terraform destroy
