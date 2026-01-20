# Deployment Guide

**Version:** 0.4.7
**Last Updated:** 2026-01-20

## Overview

This guide covers deploying PRDifferMCP to production environments, including configuration, security, reverse proxy setup, and monitoring.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Configuration](#configuration)
4. [Deployment Methods](#deployment-methods)
5. [Reverse Proxy Configuration](#reverse-proxy-configuration)
6. [Docker Deployment](#docker-deployment)
7. [Security Headers](#security-headers)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Health Checks](#health-checks)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.14.2 or higher
- **Memory**: Minimum 512MB RAM (1GB recommended)
- **CPU**: 1+ cores
- **Disk**: 100MB for installation

### External Dependencies

- **GitHub Account**: For GitHub API access
- **GitHub Personal Access Token**: For authenticated requests (recommended)

---

## Environment Setup

### Installation

```bash
# Clone repository
git clone https://github.com/CCWorkforce/PRDifferMCP.git
cd CCPRAgentsMCP

# Install dependencies
uv install --dev

# Verify installation
uv run python prdiffer/server.py --help
```

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Server Configuration
MCP_TRANSPORT=http
MCP_PORT=9102
MCP_HOST=127.0.0.1

# GitHub Token (recommended)
GITHUB_TOKEN=ghp_your_token_here

# Authentication (SECURITY: enabled by default)
MCP_AUTH_ENABLED=true
MCP_API_KEYS=your-api-key-1,your-api-key-2
MCP_ADMIN_API_KEY=your-admin-api-key

# JWT Secret (optional, for JWT auth)
MCP_JWT_SECRET=your-jwt-secret-key-min-32-chars

# Environment
ENV_FOR_DYNACONF=production
```

### Production Environment

```bash
# Set production environment
export ENV_FOR_DYNACONF=production

# Or create production settings
cat > settings.toml << EOF
[production]
app.debug = false
app.log_level = "INFO"

[auth]
enabled = true  # Always enable auth in production
EOF
```

---

## Configuration

### Production Settings

Edit `settings.toml`:

```toml
[default]
# Application
app.debug = false
app.log_level = "INFO"
app.max_files_allowed = 50

# GitHub API
github.rate_limit = 5000
github.timeout = 30
github.max_retries = 3

# Cache
cache.ttl = 600
cache.max_size = 1000
cache.enabled = true

# MCP Server
mcp.transport = "http"
mcp.port = 9102
mcp.host = "127.0.0.1"

# Authentication (SECURITY)
[auth]
enabled = true  # MUST be true in production
```

### GitHub Token Configuration

```bash
# Create GitHub Personal Access Token
# 1. Go to GitHub Settings > Developer settings > Personal access tokens
# 2. Generate token with 'repo' scope
# 3. Set as environment variable

export GITHUB_TOKEN=ghp_your_token_here

# For fine-grained tokens (recommended for production)
# Token must have: Contents (read), Pull requests (read)
```

---

## Deployment Methods

### Systemd Service

Create `/etc/systemd/system/prdiffer-mcp.service`:

```ini
[Unit]
Description=PRDifferMCP Server
After=network.target

[Service]
Type=simple
User=prdiffer
Group=prdiffer
WorkingDirectory=/opt/prdiffer-mcp
Environment="PATH=/opt/prdiffer-mcp/.venv/bin"
Environment="ENV_FOR_DYNACONF=production"
EnvironmentFile=/opt/prdiffer-mcp/.env
ExecStart=/opt/prdiffer-mcp/.venv/bin/python prdiffer/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable prdiffer-mcp
sudo systemctl start prdiffer-mcp
sudo systemctl status prdiffer-mcp
```

### Manual Service

```bash
# Start server
uv run python prdiffer/server.py

# Run in background
nohup uv run python prdiffer/server.py > logs/server.log 2>&1 &

# With specific transport
TRANSPORT=sse PORT=9102 uv run python prdiffer/server.py
```

---

## Reverse Proxy Configuration

### Nginx

Create `/etc/nginx/sites-available/prdiffer-mcp`:

```nginx
upstream prdiffer_backend {
    server 127.0.0.1:9102;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name prdiffer.example.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/prdiffer.example.com.crt;
    ssl_certificate_key /etc/ssl/private/prdiffer.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy Settings
    location /mcp {
        proxy_pass http://prdiffer_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://prdiffer_backend/health;
        access_log off;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name prdiffer.example.com;
    return 301 https://$server_name$request_uri;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/prdiffer-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Caddy

Create `Caddyfile`:

```caddyfile
prdiffer.example.com {
    reverse_proxy 127.0.0.1:9102

    # Security headers (automatic in Caddy)
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    # Health check
    handle /health {
        reverse_proxy 127.0.0.1:9102
    }

    # Log access
    log {
        output file /var/log/caddy/prdiffer-access.log
    }
}
```

### Apache

Create `/etc/apache2/sites-available/prdiffer-mcp.conf`:

```apache
<VirtualHost *:443>
    ServerName prdiffer.example.com

    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/prdiffer.example.com.crt
    SSLCertificateKeyFile /etc/ssl/private/prdiffer.example.com.key

    # Security Headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Content-Security-Policy "default-src 'self'"
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"

    # Proxy
    ProxyPreserveHost On
    ProxyPass /mcp http://127.0.0.1:9102/mcp
    ProxyPassReverse /mcp http://127.0.0.1:9102/mcp

    # Timeouts
    ProxyTimeout 60
</VirtualHost>
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.14-slim

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Install dependencies
RUN uv pip install --system .

# Copy application
COPY prdiffer/ ./prdiffer/
COPY settings.toml ./

# Create non-root user
RUN useradd -m -u 1000 prdiffer && \
    chown -R prdiffer:prdiffer /app
USER prdiffer

# Expose port
EXPOSE 9102

# Set environment
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=http
ENV MCP_PORT=9102
ENV MCP_HOST=0.0.0.0

# Run server
CMD ["python", "prdiffer/server.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  prdiffer-mcp:
    build: .
    ports:
      - "9102:9102"
    environment:
      - MCP_TRANSPORT=http
      - MCP_PORT=9102
      - MCP_HOST=0.0.0.0
      - MCP_AUTH_ENABLED=true
      - MCP_API_KEYS=${MCP_API_KEYS}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - ENV_FOR_DYNACONF=production
    volumes:
      - ./settings.toml:/app/settings.toml:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9102/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Running Docker

```bash
# Build image
docker build -t prdiffer-mcp:latest .

# Run container
docker run -d \
  --name prdiffer-mcp \
  -p 9102:9102 \
  -e MCP_AUTH_ENABLED=true \
  -e MCP_API_KEYS="your-key" \
  -e GITHUB_TOKEN="your-token" \
  prdiffer-mcp:latest

# With docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Security Headers

### Required Headers

For production deployments behind a reverse proxy, configure these headers:

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevent MIME sniffing |
| X-Frame-Options | DENY | Prevent clickjacking |
| X-XSS-Protection | 1; mode=block | XSS protection |
| Content-Security-Policy | default-src 'self' | CSP control |
| Strict-Transport-Security | max-age=31536000 | HTTPS enforcement |
| Referrer-Policy | strict-origin-when-cross-origin | Referrer control |

### TLS Configuration

```nginx
# Recommended TLS configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

---

## Monitoring and Logging

### Logging Configuration

```toml
[logging]
format = "json"  # Options: simple, json, structured
json_pretty = false  # Pretty-print JSON in development only
```

### Log Files

```bash
# Application logs
/var/log/prdiffer-mcp/

# Nginx access logs
/var/log/nginx/prdiffer-access.log

# Nginx error logs
/var/log/nginx/error.log
```

### Log Rotation

Create `/etc/logrotate.d/prdiffer-mcp`:

```
/var/log/prdiffer-mcp/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 prdiffer prdiffer
    sharedscripts
    postrotate
        systemctl reload prdiffer-mcp > /dev/null 2>&1 || true
    endscript
}
```

### Metrics Monitoring

The server exposes metrics through the metrics tracker component:

```bash
# Check metrics (if endpoint exposed)
curl http://localhost:9102/metrics
```

### Monitoring with Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'prdiffer-mcp'
    static_configs:
      - targets: ['localhost:9102']
    metrics_path: '/metrics'
```

---

## Health Checks

### Health Check Endpoint

```bash
# Check server health
curl http://localhost:9102/health

# Expected response
{
  "status": "healthy",
  "version": "0.4.7",
  "uptime": 123456
}
```

### Monitoring Health

```bash
# Systemd service status
systemctl status prdiffer-mcp

# Process check
ps aux | grep "prdiffer/server.py"

# Port check
netstat -tlnp | grep 9102

# Memory usage
ps aux | grep "prdiffer" | awk '{print $6}'
```

### Health Check Script

```bash
#!/bin/bash
# /usr/local/bin/check-prdiffer-health.sh

HEALTH_URL="http://localhost:9102/health"
TIMEOUT=5

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT $HEALTH_URL)

if [ $response -eq 200 ]; then
    echo "OK: PRDifferMCP is healthy"
    exit 0
else
    echo "CRITICAL: PRDifferMCP health check failed (HTTP $response)"
    exit 2
fi
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Check what's using port 9102
lsof -i :9102

# Kill process
kill -9 <PID>

# Or use different port
MCP_PORT=9102 uv run python prdiffer/server.py
```

#### Authentication Failures

```bash
# Verify auth is enabled
curl http://localhost:9102/mcp/status

# Check API keys
echo $MCP_API_KEYS

# Test authentication
curl -X POST http://localhost:9102/mcp/tools/get_pr_diff \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'
```

#### GitHub API Rate Limits

```bash
# Check rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit

# Reduce rate limit in settings
# Set github.rate_limit = 60 for anonymous access
```

#### Cache Issues

```bash
# Clear cache by restarting
systemctl restart prdiffer-mcp

# Or disable cache temporarily
cache.enabled = false
```

### Debug Mode

```bash
# Enable debug logging
export app.log_level=DEBUG
uv run python prdiffer/server.py

# Check configuration
uv run python -c "from prdiffer.infrastructure import get_settings_service; s = get_settings_service(); print(s.get_all())"
```

### Log Analysis

```bash
# View recent logs
journalctl -u prdiffer-mcp -n 100 -f

# Search for errors
journalctl -u prdiffer-mcp | grep -i error

# View specific time range
journalctl -u prdiffer-mcp --since "1 hour ago"
```

---

## Production Checklist

- [ ] Authentication enabled (`MCP_AUTH_ENABLED=true`)
- [ ] API keys configured (strong, unique keys)
- [ ] GitHub token configured (if needed)
- [ ] Reverse proxy configured with TLS
- [ ] Security headers enabled
- [ ] Log rotation configured
- [ ] Health checks configured
- [ ] Monitoring set up
- [ ] Backups configured (if applicable)
- [ ] Rate limiting configured
- [ ] Firewall rules configured
- [ ] Systemd service enabled
- [ ] Environment set to production
- [ ] Debug mode disabled

---

## Upgrading

### Upgrade Procedure

```bash
# Stop service
systemctl stop prdiffer-mcp

# Backup current version
cp -r /opt/prdiffer-mcp /opt/prdiffer-mcp.backup

# Pull latest changes
cd /opt/prdiffer-mcp
git pull origin main

# Update dependencies
uv sync

# Restart service
systemctl start prdiffer-mcp

# Verify
systemctl status prdiffer-mcp
curl http://localhost:9102/health
```

### Rolling Updates (Docker)

```bash
# Pull new image
docker pull prdiffer-mcp:latest

# Update container
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs
```

---

## Support

For deployment issues:
- **Issues**: [GitHub Issues](https://github.com/CCWorkforce/PRDifferMCP/issues)
- **Documentation**: [docs/](../)
- **Security**: See [SecurityUsageGuide.md](../SecurityUsageGuide.md)

---

*Last Updated: 2026-01-20*
