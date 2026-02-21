from celery import Celery
from django.conf import settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('eis')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'send-daily-digest': {
        'task': 'notifications.tasks.send_daily_digest',
        'schedule': 86400.0,  # 24 hours (daily at startup time)
    },
    'check-hot-lead-followups': {
        'task': 'notifications.tasks.check_pending_hot_leads',
        'schedule': 3600.0,  # Every hour
    },
    'send-weekly-summary': {
        'task': 'notifications.tasks.send_weekly_summary',
        'schedule': 604800.0,  # 7 days (weekly)
    },
    # Outreach tasks
    'send-outreach-emails': {
        'task': 'outreach.tasks.send_outreach_emails',
        'schedule': 3600.0,  # Every hour during business hours
    },
    'poll-email-replies': {
        'task': 'outreach.tasks.poll_email_replies',
        'schedule': 900.0,  # Every 15 minutes
    },
    'check-campaign-health': {
        'task': 'outreach.tasks.check_campaign_health',
        'schedule': 86400.0,  # Daily
    },
    'advance-warmup-weeks': {
        'task': 'outreach.tasks.advance_warmup_weeks',
        'schedule': 604800.0,  # Weekly (Mondays)
    },
}
