import boto3
import logging
from django.conf import settings
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class SESService:
    """Service for sending emails via AWS SES"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize AWS SES client"""
        try:
            self.client = boto3.client(
                'ses',
                region_name=getattr(settings, 'AWS_SES_REGION', 'us-east-1'),
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
            )
            logger.info("AWS SES client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AWS SES client: {e}")
            raise
    
    def send_email(
        self,
        to_email,
        subject,
        body_text,
        body_html=None,
        from_email=None,
        reply_to=None,
        configuration_set=None,
        message_tags=None
    ):
        """
        Send an email via AWS SES
        
        Returns: dict with 'success', 'message_id', 'error'
        """
        if not from_email:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@javisone.com')
        
        # Build message
        message = {
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': body_text}
            }
        }
        
        if body_html:
            message['Body']['Html'] = {'Data': body_html}
        
        # Build send parameters
        params = {
            'Source': from_email,
            'Destination': {'ToAddresses': [to_email]},
            'Message': message
        }
        
        if reply_to:
            params['ReplyToAddresses'] = [reply_to]
        
        if configuration_set:
            params['ConfigurationSetName'] = configuration_set
        
        if message_tags:
            params['Tags'] = [
                {'Name': k, 'Value': v}
                for k, v in message_tags.items()
            ]
        
        try:
            response = self.client.send_email(**params)
            message_id = response['MessageId']
            logger.info(f"Email sent successfully to {to_email}, MessageId: {message_id}")
            return {
                'success': True,
                'message_id': message_id,
                'error': None
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS SES ClientError ({error_code}): {error_message}")
            return {
                'success': False,
                'message_id': None,
                'error': f"{error_code}: {error_message}"
            }
        except BotoCoreError as e:
            logger.error(f"AWS SES BotoCoreError: {e}")
            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return {
                'success': False,
                'message_id': None,
                'error': str(e)
            }
    
    def verify_email_identity(self, email):
        """Request verification of an email address"""
        try:
            self.client.verify_email_identity(EmailAddress=email)
            logger.info(f"Verification request sent for {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to request verification for {email}: {e}")
            return False
    
    def get_account_sending_enabled(self):
        """Check if the account can send emails"""
        try:
            response = self.client.get_account_sending_enabled()
            return response['Enabled']
        except Exception as e:
            logger.error(f"Failed to check account sending status: {e}")
            return False
    
    def get_send_quota(self):
        """Get the sending limits for the account"""
        try:
            response = self.client.get_send_quota()
            return {
                'max_24_hour_send': response['Max24HourSend'],
                'max_send_rate': response['MaxSendRate'],
                'sent_last_24_hours': response['SentLast24Hours']
            }
        except Exception as e:
            logger.error(f"Failed to get send quota: {e}")
            return None
    
    def get_identity_verification_status(self, identity):
        """Check if an email/domain identity is verified"""
        try:
            response = self.client.get_identity_verification_attributes(
                Identities=[identity]
            )
            attrs = response['VerificationAttributes'].get(identity, {})
            return attrs.get('VerificationStatus', 'Unknown')
        except Exception as e:
            logger.error(f"Failed to get verification status for {identity}: {e}")
            return 'Error'


class WarmupService:
    """Manage domain warm-up schedule"""
    
    # Week -> Daily volume mapping
    WARMUP_SCHEDULE = {
        0: 0,   # Not started
        1: 5,   # 25/week
        2: 10,  # 50/week
        3: 15,  # 75/week
        4: 20,  # 100/week
        5: 25,  # 125/week
        6: 30,  # 150/week
        7: 35,  # 175/week - sustainable level
    }
    
    @classmethod
    def get_daily_limit(cls, warmup_week):
        """Get the daily sending limit for a given warm-up week"""
        return cls.WARMUP_SCHEDULE.get(min(warmup_week, 7), 35)
    
    @classmethod
    def get_weekly_limit(cls, warmup_week):
        """Get the weekly sending limit"""
        daily = cls.get_daily_limit(warmup_week)
        return daily * 5  # Business days only
    
    @classmethod
    def advance_week(cls, campaign):
        """Advance campaign to next warm-up week"""
        if campaign.warmup_week < 7:
            campaign.warmup_week += 1
            campaign.save(update_fields=['warmup_week'])
            logger.info(f"Campaign {campaign.name} advanced to warm-up week {campaign.warmup_week}")
        return campaign.warmup_week


class ReputationMonitor:
    """Monitor sending reputation and adjust accordingly"""
    
    BOUNCE_THRESHOLD = 0.05  # 5%
    COMPLAINT_THRESHOLD = 0.001  # 0.1%
    
    @classmethod
    def check_campaign_health(cls, campaign):
        """
        Check campaign health metrics
        Returns: dict with health status and recommendations
        """
        from .models import OutreachEmail
        
        # Get stats for last 7 days
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=7)
        
        emails = OutreachEmail.objects.filter(
            campaign=campaign,
            sent_at__gte=start_date
        )
        
        total_sent = emails.count()
        if total_sent == 0:
            return {
                'healthy': True,
                'bounce_rate': 0,
                'complaint_rate': 0,
                'recommendation': 'No emails sent in last 7 days'
            }
        
        bounced = emails.filter(status='bounced').count()
        complained = emails.filter(status='complained').count()
        
        bounce_rate = bounced / total_sent
        complaint_rate = complained / total_sent
        
        healthy = bounce_rate < cls.BOUNCE_THRESHOLD and complaint_rate < cls.COMPLAINT_THRESHOLD
        
        recommendation = 'Continue normal operations'
        if bounce_rate >= cls.BOUNCE_THRESHOLD:
            recommendation = 'PAUSE: Bounce rate too high. Clean list before continuing.'
        elif complaint_rate >= cls.COMPLAINT_THRESHOLD:
            recommendation = 'PAUSE: Complaint rate too high. Review messaging before continuing.'
        
        return {
            'healthy': healthy,
            'bounce_rate': round(bounce_rate * 100, 2),
            'complaint_rate': round(complaint_rate * 100, 3),
            'total_sent': total_sent,
            'bounced': bounced,
            'complained': complained,
            'recommendation': recommendation
        }
