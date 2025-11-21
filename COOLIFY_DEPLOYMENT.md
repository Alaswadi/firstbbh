# Coolify VPS Deployment Guide

## 🚀 Deploying to Coolify

This guide will help you deploy the production-ready bug bounty automation to your Coolify VPS.

## 📋 Prerequisites

- Coolify VPS with Docker installed
- Git repository (GitHub, GitLab, etc.)
- Domain name (optional, but recommended)

## 🔧 Step 1: Push Code to Git Repository

```bash
# Initialize git if not already done
cd "c:\Users\fadia\Documents\augment-projects\bug bounty automations\firstbbh"
git init
git add .
git commit -m "Production-ready setup with Celery, Redis, PostgreSQL"

# Add your remote repository
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

## 🎯 Step 2: Create Application in Coolify

### Option A: Using Docker Compose (Recommended)

1. **Login to Coolify Dashboard**
2. **Create New Resource** → **Docker Compose**
3. **Connect Git Repository**
   - Select your repository
   - Branch: `main`
   - Build Pack: `Docker Compose`

4. **Configure Environment Variables**

Click on "Environment Variables" and add:

```env
# Database
DB_NAME=bbh_automation
DB_USER=bbh_user
DB_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# Flask
SECRET_KEY=YOUR_SUPER_SECRET_KEY_HERE
FLASK_ENV=production

# Redis (use default, Coolify will handle)
REDIS_HOST=redis
REDIS_PORT=6379

# Flower Authentication
FLOWER_BASIC_AUTH=admin:YOUR_FLOWER_PASSWORD_HERE
```

5. **Configure Domains**
   - Main app: `your-domain.com` → Port 80 (nginx)
   - Flower: `flower.your-domain.com` → Port 5555

6. **Deploy**
   - Click "Deploy"
   - Coolify will build and start all services

### Option B: Separate Services (Alternative)

If Coolify doesn't support multi-service compose well, deploy services separately:

#### 1. PostgreSQL Database
- Create **PostgreSQL** database in Coolify
- Note the connection details
- Update environment variables accordingly

#### 2. Redis Cache
- Create **Redis** instance in Coolify
- Note the connection URL
- Update environment variables

#### 3. Main Application
- Create **Docker** application
- Use custom Dockerfile
- Set build command: `docker build -t bbh-app .`
- Set start command: `gunicorn --bind 0.0.0.0:5050 --workers 4 app:app`

## 🔐 Step 3: Security Configuration

### Update Environment Variables

In Coolify, set these environment variables:

```env
# CRITICAL: Change these!
SECRET_KEY=generate-a-long-random-string-here
DB_PASSWORD=use-a-strong-password-here
FLOWER_BASIC_AUTH=admin:strong-password-here

# Database (if using Coolify's PostgreSQL)
DB_HOST=your-postgres-service-name
DB_PORT=5432
DB_NAME=bbh_automation
DB_USER=bbh_user

# Redis (if using Coolify's Redis)
REDIS_HOST=your-redis-service-name
REDIS_PORT=6379
REDIS_URL=redis://your-redis-service-name:6379/0

# Celery
CELERY_BROKER_URL=redis://your-redis-service-name:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-service-name:6379/1
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate strong password
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

## 🌐 Step 4: Domain Configuration

### Main Application
- Domain: `bbh.yourdomain.com`
- Port: `80` (nginx service)
- SSL: Enable in Coolify (automatic Let's Encrypt)

### Flower Monitoring
- Domain: `flower.yourdomain.com`
- Port: `5555`
- SSL: Enable in Coolify

## 📦 Step 5: Persistent Storage

In Coolify, configure persistent volumes:

1. **PostgreSQL Data**
   - Volume: `postgres_data` → `/var/lib/postgresql/data`

2. **Redis Data**
   - Volume: `redis_data` → `/data`

3. **Application Output**
   - Volume: `output` → `/app/output`

4. **Application Data**
   - Volume: `data` → `/app/data`

## 🔍 Step 6: Verify Deployment

### Check Service Status

In Coolify dashboard:
- All services should show "Running"
- Check logs for any errors

### Test Application

1. **Access Main App**
   ```
   https://bbh.yourdomain.com
   ```

2. **Access Flower**
   ```
   https://flower.yourdomain.com
   ```

3. **Run Test Scan**
   - Navigate to main app
   - Click "New Scan"
   - Enter test domain
   - Monitor progress

### Check Logs

In Coolify:
- Click on each service
- View "Logs" tab
- Look for errors

## 🐛 Troubleshooting

### Services Won't Start

**Check logs in Coolify:**
```
Service → Logs
```

**Common issues:**
- Missing environment variables
- Database connection failed
- Redis connection failed

### Database Connection Error

**Solution:**
1. Verify PostgreSQL service is running
2. Check DB_HOST, DB_USER, DB_PASSWORD in environment variables
3. Ensure services are in same network

### Celery Workers Not Processing

**Solution:**
1. Check celery_worker logs
2. Verify Redis connection
3. Restart celery_worker service

### Can't Access Application

**Solution:**
1. Check nginx service is running
2. Verify domain DNS points to VPS IP
3. Check Coolify proxy settings
4. Ensure port 80/443 are open

## 📊 Monitoring

### Application Logs
```
Coolify Dashboard → Your App → Logs
```

### Celery Tasks
```
https://flower.yourdomain.com
```

### Database
```
Coolify Dashboard → PostgreSQL → Logs
```

## 🔄 Updates & Redeployment

### Push Updates
```bash
git add .
git commit -m "Update description"
git push
```

### Redeploy in Coolify
1. Go to your application
2. Click "Redeploy"
3. Coolify will pull latest code and rebuild

## 🎯 Production Checklist

- [ ] Changed all default passwords
- [ ] Set strong SECRET_KEY
- [ ] Configured custom domain
- [ ] Enabled SSL/HTTPS
- [ ] Set up persistent volumes
- [ ] Configured Flower authentication
- [ ] Tested scan execution
- [ ] Verified all services running
- [ ] Checked logs for errors
- [ ] Set up monitoring alerts (optional)

## 💡 Tips

1. **Use Coolify's Built-in Services**
   - PostgreSQL and Redis can be created directly in Coolify
   - Easier management and automatic backups

2. **Enable Automatic Deployments**
   - Configure webhook in Coolify
   - Auto-deploy on git push

3. **Monitor Resource Usage**
   - Check CPU/RAM in Coolify dashboard
   - Scale workers if needed

4. **Regular Backups**
   - Enable automatic backups in Coolify
   - Backup PostgreSQL database regularly

## 🆘 Support

If you encounter issues:
1. Check Coolify logs
2. Review service-specific logs
3. Verify environment variables
4. Check network connectivity between services

## 📝 Next Steps

After successful deployment:
1. Run your first scan
2. Monitor in Flower dashboard
3. Check results in database
4. Set up scheduled scans (optional)
5. Configure alerting (optional)
