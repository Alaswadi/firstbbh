# Quick Start Guide for Coolify Deployment

## 🚀 Deploy in 5 Minutes

### 1. Prepare Your Repository

```bash
# Navigate to project
cd "c:\Users\fadia\Documents\augment-projects\bug bounty automations\firstbbh"

# Commit all changes
git add .
git commit -m "Production-ready for Coolify"
git push
```

### 2. Create in Coolify

1. Login to Coolify
2. **New Resource** → **Docker Compose**
3. Connect your Git repository
4. Select branch: `main`

### 3. Set Environment Variables

In Coolify, add these variables:

```
SECRET_KEY=<generate-random-string>
DB_PASSWORD=<your-secure-password>
FLOWER_BASIC_AUTH=admin:<your-password>
```

**Generate secure values:**
```bash
# Run on your local machine
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"
```

### 4. Configure Domains (Optional)

- Main App: `your-domain.com` → Port 80
- Flower: `flower.your-domain.com` → Port 5555

### 5. Deploy

Click **Deploy** in Coolify!

## ✅ Verify

1. Check all services are "Running" in Coolify
2. Access your domain
3. Create a test scan
4. Monitor in Flower dashboard

## 📚 Full Documentation

See [COOLIFY_DEPLOYMENT.md](./COOLIFY_DEPLOYMENT.md) for detailed instructions.

## 🆘 Quick Troubleshooting

**Services won't start?**
- Check logs in Coolify dashboard
- Verify environment variables are set
- Ensure DB_PASSWORD is set

**Can't access app?**
- Check domain DNS settings
- Verify port 80 is exposed
- Check nginx service logs

**Scans not running?**
- Check celery_worker logs
- Verify Redis is running
- Restart celery_worker service
