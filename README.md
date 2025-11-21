# Production-Ready Bug Bounty Automation

A comprehensive bug bounty automation platform with asynchronous task processing, real-time monitoring, and scalable architecture.

**Optimized for Coolify VPS Deployment**

## 🚀 Quick Deploy to Coolify

```bash
# 1. Push to Git
git add .
git commit -m "Production setup"
git push

# 2. In Coolify: New Resource → Docker Compose
# 3. Connect repository and set environment variables
# 4. Deploy!
```

**See [QUICKSTART.md](./QUICKSTART.md) for detailed 5-minute deployment guide.**

## 🏗️ Features

- **Asynchronous Scanning**: Non-blocking scans using Celery task queue
- **Real-time Progress**: Live task status updates and progress tracking
- **Scalable Architecture**: PostgreSQL database with connection pooling
- **Distributed Processing**: Multiple Celery workers for parallel execution
- **Monitoring Dashboard**: Flower UI for task and worker monitoring
- **Production-Ready**: Nginx reverse proxy with rate limiting and security headers
- **Persistent Storage**: PostgreSQL for data, Redis for caching and message brokering
- **Coolify Optimized**: Ready for one-click deployment on Coolify VPS

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│    Nginx    │─────▶│  Flask App  │─────▶│    Redis    │
│   (Port 80) │      │ (Gunicorn)  │      │  (Broker)   │
└─────────────┘      └─────────────┘      └──────┬──────┘
                            │                     │
                            ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐
                     │ PostgreSQL  │      │   Celery    │
                     │  Database   │      │   Workers   │
                     └─────────────┘      └─────────────┘
```

## 📋 Prerequisites

- Coolify VPS with Docker
- Git repository (GitHub, GitLab, etc.)
- Domain name (optional but recommended)

## 🔧 Installation

### For Coolify VPS (Recommended)

**Quick Start:** See [QUICKSTART.md](./QUICKSTART.md)

**Full Guide:** See [COOLIFY_DEPLOYMENT.md](./COOLIFY_DEPLOYMENT.md)

**Summary:**
1. Push code to Git repository
2. Create Docker Compose app in Coolify
3. Set environment variables (SECRET_KEY, DB_PASSWORD, FLOWER_BASIC_AUTH)
4. Deploy!

### For Local Development

1. **Clone the repository**
   ```bash
   cd "c:\Users\fadia\Documents\augment-projects\bug bounty automations\firstbbh"
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and change the passwords and secret keys
   ```

3. **Build and start services**
   ```bash
   docker-compose up -d --build
   ```

4. **Check service status**
   ```bash
   docker-compose ps
   ```

## 🌐 Access Points

- **Main Application**: http://localhost (or your server IP)
- **Flower Monitoring**: http://localhost/flower
- **Direct Flask App**: http://localhost:5050
- **Direct Flower**: http://localhost:5555

## 📖 Usage

### Starting a Scan

1. Navigate to http://localhost
2. Click "New Scan"
3. Enter target domain
4. Select scan type and tools
5. Submit and monitor progress in real-time

### Monitoring Tasks

- **Task Status Page**: Automatically redirected after starting a scan
- **Flower Dashboard**: http://localhost/flower for detailed worker and task monitoring

### API Endpoints

- `GET /api/scans` - List all scans
- `GET /api/scan/<id>` - Get scan details
- `GET /api/task/<task_id>/status` - Get task status
- `POST /api/task/<task_id>/cancel` - Cancel running task

## 🛠️ Management Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f postgres
```

### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart celery_worker
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Data
```bash
docker-compose down -v
```

### Scale Celery Workers
```bash
docker-compose up -d --scale celery_worker=4
```

## 🗄️ Database Management

### Access PostgreSQL
```bash
docker-compose exec postgres psql -U bbh_user -d bbh_automation
```

### Backup Database
```bash
docker-compose exec postgres pg_dump -U bbh_user bbh_automation > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker-compose exec -T postgres psql -U bbh_user -d bbh_automation
```

## 🔐 Security Considerations

1. **Change default passwords** in `.env` file
2. **Use strong SECRET_KEY** for Flask
3. **Enable HTTPS** in production (uncomment SSL config in nginx.conf)
4. **Restrict Flower access** with strong authentication
5. **Use firewall rules** to limit access to sensitive ports

## 🐛 Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose up -d --build
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres
```

### Celery tasks not executing
```bash
# Check worker status
docker-compose logs celery_worker

# Restart workers
docker-compose restart celery_worker
```

### Redis connection errors
```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# Should return: PONG
```

## 📊 Monitoring

### Flower Dashboard
Access http://localhost/flower to view:
- Active tasks
- Worker status
- Task history
- Task success/failure rates

### Health Checks
```bash
# Nginx health check
curl http://localhost/health

# Redis health check
docker-compose exec redis redis-cli ping

# PostgreSQL health check
docker-compose exec postgres pg_isready
```

## 🔄 Updating

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## 📝 Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DB_PASSWORD` - PostgreSQL password
- `SECRET_KEY` - Flask secret key
- `FLOWER_BASIC_AUTH` - Flower authentication (format: username:password)
- `MAX_WORKERS` - Number of concurrent workers
- `BATCH_SIZE` - Batch size for processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details
