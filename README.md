# EIS Backend - Executive Intelligence System

A Django-based backend for managing pilot applications, lead scoring, and executive workflows for JavisOne.

## Features

- **Pilot Application Management**: Capture and process executive pilot applications
- **Qualification Scoring**: Automated lead scoring (0-100) based on organization profile
- **Lead Pipeline**: Kanban-style lead management with status tracking
- **Activity Tracking**: Complete audit trail of all lead interactions
- **Notifications**: Slack and email alerts based on priority tiers
- **File Uploads**: Secure sample report uploads with type validation
- **Rate Limiting**: 5 submissions per IP per hour

## Tech Stack

- Django 5.x with Django REST Framework
- PostgreSQL (database)
- Redis (Celery broker)
- Celery (async tasks)
- python-decouple (environment configuration)

## Project Structure

```
eis-backend/
├── config/                    # Django project configuration
│   ├── settings/
│   │   ├── base.py           # Base settings
│   │   ├── development.py    # Development settings
│   │   └── production.py     # Production settings
│   ├── urls.py               # Root URL configuration
│   └── wsgi.py
├── leads/                     # Pilot applications & lead management
│   ├── models.py             # PilotApplication model
│   ├── serializers.py        # DRF serializers
│   ├── views.py              # API views
│   ├── admin.py              # Django admin configuration
│   ├── scoring.py            # Qualification scoring algorithm
│   └── urls.py               # Lead API URLs
├── activities/                # Lead activity tracking
│   ├── models.py             # LeadActivity model
│   ├── serializers.py
│   └── views.py
├── pilots/                    # Active pilot management
│   ├── models.py             # PilotEngagement, AlignmentCall models
│   ├── serializers.py
│   └── views.py
├── notifications/             # Slack/email notifications
│   ├── tasks.py              # Celery notification tasks
│   └── utils.py              # Notification utilities
├── uploads/                   # File uploads directory
├── static/                    # Static files
├── templates/                 # Django templates
├── manage.py
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Clone and Setup

```bash
cd /Users/media/workspace/eis-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb eis_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

### 5. Run Celery Worker (for notifications)

```bash
celery -A config worker -l info
```

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pilot-applications/` | Submit new application |
| GET | `/api/v1/pilot-applications/{id}/status/` | Check application status |

### Admin Endpoints (Requires Authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/leads/` | List all leads |
| GET | `/api/v1/admin/leads/{id}/` | Lead details |
| PATCH | `/api/v1/admin/leads/{id}/` | Update lead |
| POST | `/api/v1/admin/leads/{id}/activities/` | Log activity |
| POST | `/api/v1/admin/leads/{id}/schedule-call/` | Schedule alignment call |

## Qualification Scoring

Applications are scored 0-100 based on:

- **Team Size** (0-25 pts): 500+=25, 101-500=20, 21-100=15, 1-20=5
- **Organizational Scope** (0-25 pts): National-Level=25, Multi-Country=20, Multi-Region=15, Single Location=5
- **Industry** (0-20 pts): Government=20, NGO=18, Healthcare=15, Fintech=15, Manufacturing=10, Religious=12, Other=5
- **Challenge Severity** (0-15 pts): Risk & Compliance=15, Fragmented Reporting=12, KPI Gaps=12, Slow Decisions=10, Complexity=8, Other=5
- **File Upload** (+10 pts): Bonus for sample report

**Priority Tiers:**
- **Hot** (80-100): Immediate response (4h)
- **Warm** (60-79): Same day response
- **Cool** (40-59): Next day response
- **Nurture** (0-39): Automated sequence

## Environment Variables

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgres://user:pass@localhost:5432/eis_db
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=https://javisone.com,https://www.javisone.com

# Rate Limiting
RATE_LIMIT=5/hour

# Slack Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@javisone.com

# File Uploads
MAX_UPLOAD_SIZE=10485760  # 10MB
```

## Frontend Integration

The React frontend at `/Users/media/workspace/eis-web/` has been updated to:

1. POST form data to `/api/v1/pilot-applications/`
2. Handle loading states and error responses
3. Display success confirmation with tracking info

Update the API base URL in the frontend:
```typescript
const API_BASE = process.env.VITE_API_URL || 'https://api.javisone.com';
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Configure production database
- [ ] Set up Redis instance
- [ ] Configure CORS for production domain
- [ ] Set up Slack webhook
- [ ] Configure email SMTP
- [ ] Set up SSL certificate
- [ ] Configure rate limiting
- [ ] Set up Celery worker as systemd service

### Docker Deployment

```bash
docker-compose up -d
```

## License

Private - JavisOne Internal Use
