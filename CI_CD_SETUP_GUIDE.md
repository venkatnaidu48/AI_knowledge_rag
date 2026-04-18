# 🚀 CI/CD Pipeline Setup Guide

## Overview

The RAG application now has a complete CI/CD pipeline using **GitHub Actions** that automates:

✅ **Testing** - Unit and integration tests  
✅ **Code Quality** - Linting, formatting, security checks  
✅ **Building** - Docker image creation  
✅ **Deployment** - Staging and production environments  
✅ **Monitoring** - Performance and load testing  

---

## 📋 Workflows Included

### 1. **CI Workflow** (`.github/workflows/ci.yml`)
**Triggers:** On every push and pull request to `main` or `develop`

**Jobs:**
- **test** - Runs pytest on Python 3.9, 3.10, 3.11
- **code-quality** - Black, isort, pylint checks
- **security** - Bandit security scan, dependency vulnerabilities
- **build** - Docker image build

**Output:**
- Test coverage report
- Code quality metrics
- Security scan results
- Docker image (tagged with commit SHA)

### 2. **Deploy Workflow** (`.github/workflows/deploy.yml`)
**Triggers:** On push to `main` branch and manual trigger

**Jobs:**
- **build-and-push** - Build and push to Docker registries
- **deploy-staging** - Deploy to staging (on develop push)
- **deploy-production** - Deploy to production (on main push)

**Registries:**
- Docker Hub
- GitHub Container Registry (GHCR)

### 3. **Performance Workflow** (`.github/workflows/performance.yml`)
**Triggers:** Daily at 2 AM UTC or manual trigger

**Jobs:**
- **performance-test** - Runs API performance tests
- **load-test** - Simulates 100 concurrent users

---

## 🔧 Setup Instructions

### Step 1: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and add:

```
DOCKER_USERNAME         → Your Docker Hub username
DOCKER_PASSWORD         → Your Docker Hub token
STAGING_DEPLOY_KEY      → Staging deployment SSH key
PROD_DEPLOY_KEY         → Production deployment SSH key
GRAFANA_PASSWORD        → Grafana admin password
DB_USER                 → PostgreSQL username
DB_PASSWORD             → PostgreSQL password
REDIS_PASSWORD          → Redis password
OPENAI_API_KEY          → OpenAI API key (optional)
GROQ_API_KEY            → Groq API key (optional)
```

**How to add secrets:**
1. Go to repository Settings
2. Click "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Add each secret name and value

### Step 2: Enable GitHub Actions

1. Go to repository → Actions
2. Confirm "Workflows have permission to run"
3. All workflows should now be visible

### Step 3: Configure Branch Protection Rules

1. Go to Settings → Branches
2. Add rule for `main` branch:
   - ✅ Require status checks to pass before merging
   - ✅ Select all CI jobs (test, code-quality, security, build)
   - ✅ Require code review before merging
   - ✅ Dismiss stale pull request approvals

### Step 4: Set Up Docker Registry

**For Docker Hub:**
```bash
# Log in to Docker Hub
docker login

# Create an Access Token at https://hub.docker.com/settings/security
# Use token instead of password for DOCKER_PASSWORD secret
```

**For GitHub Container Registry:**
- Automatically configured via `GITHUB_TOKEN`
- No additional setup needed

### Step 5: Configure Deployment Targets

Update deployment scripts in `.github/workflows/deploy.yml`:

**For Kubernetes:**
```yaml
- name: Deploy to production
  run: |
    kubectl apply -f k8s/production/deployment.yml
  env:
    KUBECONFIG: ${{ secrets.KUBECONFIG }}
```

**For Docker Compose on VPS:**
```yaml
- name: Deploy to production
  run: |
    ssh -i deploy_key user@server \
      'cd /app && docker-compose pull && docker-compose up -d'
```

---

## 📊 Workflow Status Dashboard

View all workflow runs:
1. Go to repository → Actions
2. Click on workflow name to see history
3. Click on specific run to see details

**Sample workflow output:**
```
✅ test (3.9, 3.10, 3.11)      [23 tests passed]
✅ code-quality                [0 issues found]
✅ security                    [No vulnerabilities]
✅ build                       [Docker image created]
✅ deploy-production           [Deployed successfully]
```

---

## 🛠️ Local Testing Before Push

### Run CI Checks Locally

**1. Install pre-commit hooks:**
```bash
pip install pre-commit
pre-commit install
```

**2. Run all checks manually:**
```bash
# Tests
pytest tests/ -v

# Code quality
black src tests
isort src tests
pylint src

# Security
bandit -r src
safety check

# Docker build
docker build -t rag-system:test -f deployment/Dockerfile .
```

**3. Or use the Makefile:**
```bash
make test          # Run tests
make lint          # Run linting
make security      # Run security checks
make build-image   # Build Docker image
```

---

## 🔐 Security Best Practices

### Secrets Management

✅ **DO:**
- Use GitHub Secrets for all sensitive data
- Rotate secrets regularly
- Use scoped tokens (not admin tokens)
- Enable secret scanning

❌ **DON'T:**
- Commit secrets to repository
- Use hardcoded credentials in workflows
- Share secrets in logs or outputs

### Branch Protection

Enable these rules for `main` branch:
- ✅ Require status checks to pass
- ✅ Require code reviews
- ✅ Require branches to be up to date
- ✅ Require conversation resolution

---

## 📈 Monitoring Workflows

### View Workflow Runs

```bash
# Using GitHub CLI
gh run list --repo your-org/rag-application

# View specific run
gh run view <run-id> --repo your-org/rag-application
```

### Notification Settings

1. Go to Settings → Notifications
2. Configure alerts for:
   - ✅ All workflow runs
   - ✅ Failed workflow runs (recommended)
   - ✅ Deployment failures

---

## 🐛 Troubleshooting

### Issue: "Workflow file not found"

**Solution:**
```bash
# Ensure workflows are in correct location
.github/workflows/ci.yml
.github/workflows/deploy.yml
.github/workflows/performance.yml

# Commit and push
git add .github/
git commit -m "Add CI/CD workflows"
git push
```

### Issue: "Docker build fails in CI"

**Solution:**
```bash
# Check Dockerfile
docker build -t test -f deployment/Dockerfile .

# Check for missing files
ls deployment/Dockerfile
ls requirements.txt

# Update workflow if needed
```

### Issue: "Tests fail in CI but pass locally"

**Solutions:**
- Check Python version (use 3.11 for testing)
- Verify all dependencies in requirements.txt
- Run with same pytest config: `pytest --config-file pytest.ini`
- Check file paths (use absolute paths)

### Issue: "Deployment secret not working"

**Solution:**
```bash
# Verify secret name matches exactly (case-sensitive)
# Check secret is available in Actions settings
# Ensure workflow can access it: needs "contents: read, packages: write"
```

---

## 📋 Workflow Configuration Files

### Main CI Workflow Variables

**`.github/workflows/ci.yml`**
```yaml
python-version: ['3.9', '3.10', '3.11']
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

### Deployment Triggers

**`.github/workflows/deploy.yml`**
```yaml
on:
  push:
    branches: [main]
    tags: ['v*']  # Trigger on version tags
  workflow_dispatch:  # Manual trigger
```

---

## 🚀 Deployment Pipeline

### Automatic Deployment

```
Push to main
    ↓
✅ CI checks pass
    ↓
✅ Docker image built and pushed
    ↓
✅ Deployed to production
    ↓
✅ Health checks pass
    ↓
✅ Monitoring active
```

### Manual Deployment

1. Go to repository → Actions
2. Select "Deploy" workflow
3. Click "Run workflow"
4. Select branch and click "Run workflow"

---

## 📊 Performance Metrics

### Typical CI/CD Times

```
Tests:           5-10 minutes
Code Quality:    2-3 minutes
Security:        1-2 minutes
Docker Build:    3-5 minutes
Deployment:      2-5 minutes
───────────────────────────
Total:          13-25 minutes (parallel execution)
```

---

## ✨ Next Steps

1. ✅ Push code to GitHub
2. ✅ Monitor first workflow run
3. ✅ Configure branch protection
4. ✅ Set up deployment targets
5. ✅ Monitor production deployment

---

## 📞 Support

### Debugging Workflow Runs

```bash
# Enable debug logging
export ACTIONS_STEP_DEBUG=true

# Re-run workflow
gh run rerun <run-id>
```

### View Logs

1. Go to repository → Actions
2. Click on workflow run
3. Click on job to see logs
4. Search for errors or failures

---

## 📄 Quick Reference

| Task | Command |
|------|---------|
| View workflows | `gh run list` |
| View specific run | `gh run view <id>` |
| Rerun failed | `gh run rerun <id>` |
| Cancel run | `gh run cancel <id>` |
| View logs | GitHub Actions UI |

---

**CI/CD Status: ✅ 100% COMPLETE**

Your project now has a production-ready CI/CD pipeline! 🚀
