# Lumina CI/CD Guide

GitHub Actions workflows for automated testing, security scanning, and performance monitoring.

---

## Workflows Overview

### 1. Main CI Workflow ([ci.yml](../.github/workflows/ci.yml))

**Triggers**: Push to main/develop, Pull Requests, Manual

**Jobs**:
| Job | Purpose | Duration |
|-----|---------|----------|
| `lint` | Code quality checks (ruff, bandit) | ~2 min |
| `unit-tests` | Pytest unit tests (matrix: OS + Python) | ~5 min |
| `integration-tests` | E2E tests with services | ~10 min |
| `security-tests` | Security scanning | ~3 min |
| `performance-tests` | Performance benchmarks | ~5 min |
| `build` | Build Electron app | ~15 min |

**Example**:
```bash
# Trigger manually
gh workflow run ci.yml

# View results
gh run view --web
```

### 2. Security Scan Workflow ([security-scan.yml](../.github/workflows/security-scan.yml))

**Triggers**: Daily (2 AM UTC), Push to main/develop, PRs, Manual

**Jobs**:
| Job | Tool | Purpose |
|-----|------|---------|
| `bandit-scan` | bandit | Python security linter |
| `safety-scan` | safety | Dependency vulnerability check |
| `secrets-scan` | TruffleHog | Secrets detection |
| `pytest-security` | pytest | Security test suite |
| `snyk-scan` | snyk | Additional security (optional) |

**Example**:
```bash
# Run security scan manually
gh workflow run security-scan.yml

# Download reports
gh run download <run-id> -n security-reports
```

### 3. Performance Workflow ([performance.yml](../.github/workflows/performance.yml))

**Triggers**: Push to main/develop, PRs, Manual

**Jobs**:
| Job | Purpose |
|-----|---------|
| `benchmarks` | Run pytest-benchmark, store history |
| `memory-leaks` | Memory leak detection tests |
| `load-tests` | Locust load testing (manual only) |
| `regression-check` | Compare PR vs baseline (PRs only) |

**Example**:
```bash
# Trigger load tests (manual only)
gh workflow run performance.yml

# View benchmark history
# https://github.com/<owner>/<repo>/devops/benchmarks
```

---

## Quick Start

### 1. Enable GitHub Actions

```bash
# Push to GitHub (workflows auto-enable)
git push origin main
```

### 2. Configure Secrets (Optional)

```bash
# For Snyk security scanning
gh secret set SNYK_TOKEN --body "your-snyk-token"

# For Codecov
gh secret set CODECOV_TOKEN --body "your-codecov-token"
```

### 3. Configure Branch Protection

```bash
# Require CI checks before merge
gh api repos/:owner/:repo/branches/main/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["ci", "security-scan"]
  },
  "enforce_admins": true,
  "require_pull_request_reviews": true
}
EOF
```

---

## Badge Examples

Add to README.md:

```markdown
[![CI](https://github.com/your-org/lumina/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/lumina/actions/workflows/ci.yml)
[![Security](https://github.com/your-org/lumina/actions/workflows/security-scan.yml/badge.svg)](https://github.com/your-org/lumina/actions/workflows/security-scan.yml)
[![Performance](https://github.com/your-org/lumina/actions/workflows/performance.yml/badge.svg)](https://github.com/your-org/lumina/actions/workflows/performance.yml)
```

---

## Local Testing

### Run tests locally before pushing:

```bash
# Unit tests
cd automation
pytest tests_pytest/ -v -m "not integration"

# Security scan
bandit -r ../python_backend/
safety check --file ../python_backend/requirements.txt

# Performance benchmarks
pytest tests_pytest/performance/ --benchmark-only
```

---

## Troubleshooting

### Workflow not triggering?

```bash
# Check workflow syntax
gh workflow view ci.yml --yaml

# Test manually
gh workflow run ci.yml
```

### Tests passing locally but failing in CI?

- Check Python version mismatch
- Verify PYTHONPATH settings
- Check for missing dependencies

### Security scan false positives?

Add `# nosec` comment or configure `.bandit` file:

```toml
# .bandit
[bandit]
exclude_dirs = ['/tests']
skips = ['B101']
```

---

## CI/CD Best Practices

1. **Fast Feedback**: Keep unit tests under 5 minutes
2. **Parallel Jobs**: Use matrix strategy for OS/Python versions
3. **Caching**: Cache pip dependencies and node_modules
4. **Artifacts**: Keep reports for 7-30 days depending on importance
5. **Notifications**: Configure Slack/Discord webhooks for failures
6. **Branch Protection**: Require checks before merging
7. **Secret Scanning**: Never commit credentials or API keys
8. **Performance Baselines**: Alert on >50% regression
9. **Security**: Run daily automated scans
10. **Documentation**: Keep this guide updated

---

## Advanced Configuration

### Custom workflow dispatch inputs:

```yaml
on:
  workflow_dispatch:
    inputs:
      test_type:
        description: 'Test type'
        required: true
        type: choice
        options:
          - unit
          - integration
          - all
```

### Self-hosted runners for private dependencies:

```yaml
jobs:
  test:
    runs-on: [self-hosted, linux]
```

### Caching strategy:

```yaml
- name: Cache pip
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

---

## Monitoring and Alerts

### Set up status checks:

```bash
# List all status checks
gh api repos/:owner/:repo/branches/main/protection
```

### Configure notifications:

1. Go to Repository Settings → Notifications
2. Configure email/Slack alerts
3. Subscribe to workflow failure events

### View workflow analytics:

```bash
# Workflow run times
gh run list --workflow=ci.yml --json databaseId,conclusion,createdAt

# Failed runs
gh run list --workflow=ci.yml --json conclusion --jq '.[] | select(.conclusion=="failure")'
```

---

## CI/CD Maintenance

### Update dependencies:

```bash
# GitHub Actions versions
- uses: actions/checkout@v4  # Update to latest
- uses: actions/setup-python@v5
```

### Clean up old workflow runs:

```bash
# Delete runs older than 90 days
gh run list --json databaseId --limit 1000 \
  | jq '.[].databaseId' \
  | xargs -I {} gh run delete {}  # Requires admin
```

### Monitor quota usage:

```bash
# View minutes used
gh api /repos/:owner/:repo/actions/usage
```

---

## Cost Optimization

| Strategy | Savings |
|----------|---------|
| Cancel redundant workflows | ~30% |
| Use smart caching | ~20% |
| Reduce matrix size | ~40% |
| Self-hosted runners | ~60% |

---

## Further Reading

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest-benchmark Docs](https://pytest-benchmark.readthedocs.io/)
- [Bandit Security Docs](https://bandit.readthedocs.io/)
- [Locust Load Testing](https://locust.io/)
