"""
IMAP Email Receiver for cPanel Webmail
Polls inbox for replies and processes them into the outreach system
"""
import imaplib
import email
from email.header import decode_header
import logging
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from outreach.models import OutreachEmail, Engagement
from outreach.sequencer import EmailSequencer

logger = logging.getLogger(__name__)


class IMAPReceiver:
    """Receive and process emails from cPanel IMAP"""
    
    def __init__(self):
        self.host = getattr(settings, 'IMAP_HOST', 'mail.javisone.com')
        self.port = getattr(settings, 'IMAP_PORT', 993)
        self.username = getattr(settings, 'IMAP_USERNAME', 'javis@javisone.com')
        self.password = getattr(settings, 'IMAP_PASSWORD', '')
        self.use_ssl = True
        self.connection = None
    
    def connect(self):
        """Connect to IMAP server"""
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self.connection = imaplib.IMAP4(self.host, self.port)
            
            self.connection.login(self.username, self.password)
            logger.info(f"Connected to IMAP server: {self.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            return False
    
    def disconnect(self):
        """Close IMAP connection"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.error(f"Error disconnecting from IMAP: {e}")
    
    def fetch_unread(self, folder='INBOX', limit=50):
        """Fetch unread messages from inbox"""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            # Select folder
            status, messages = self.connection.select(folder)
            if status != 'OK':
                logger.error(f"Could not select folder {folder}")
                return []
            
            # Search for unread messages
            status, data = self.connection.search(None, 'UNSEEN')
            if status != 'OK':
                logger.warning("No unread messages found")
                return []
            
            message_ids = data[0].split()
            if limit:
                message_ids = message_ids[:limit]
            
            emails = []
            for msg_id in message_ids:
                status, msg_data = self.connection.fetch(msg_id, '(RFC822)')
                if status == 'OK':
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    email_data = self.parse_email(msg, msg_id.decode())
                    if email_data:
                        emails.append(email_data)
                    
                    # Mark as read (optional - you might want to keep unread in cPanel)
                    # self.connection.store(msg_id, '+FLAGS', '\\Seen')
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def parse_email(self, msg, msg_id):
        """Parse email message into dict"""
        try:
            # Get subject
            subject = self.decode_header_value(msg.get('Subject', ''))
            
            # Get sender
            from_email = self.decode_header_value(msg.get('From', ''))
            from_address = self.extract_email(from_email)
            
            # Get date
            date_str = msg.get('Date', '')
            
            # Get message ID (for threading)
            message_id = msg.get('Message-ID', '')
            
            # Get in-reply-to (to match with sent email)
            in_reply_to = msg.get('In-Reply-To', '')
            references = msg.get('References', '')
            
            # Get body
            body = self.get_email_body(msg)
            
            return {
                'msg_id': msg_id,
                'message_id': message_id,
                'subject': subject,
                'from': from_email,
                'from_address': from_address,
                'date': date_str,
                'in_reply_to': in_reply_to,
                'references': references,
                'body': body,
                'raw': msg,
            }
        except Exception as e:
            logger.error(f"Error parsing email {msg_id}: {e}")
            return None
    
    def decode_header_value(self, value):
        """Decode email header value"""
        if not value:
            return ''
        
        decoded_parts = decode_header(value)
        result = ''
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(charset or 'utf-8', errors='replace')
            else:
                result += part
        return result
    
    def extract_email(self, from_header):
        """Extract email address from From header"""
        import re
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1)
        # If no angle brackets, assume the whole thing is an email
        match = re.search(r'[\w\.-]+@[\w\.-]+', from_header)
        if match:
            return match.group(0)
        return from_header
    
    def get_email_body(self, msg):
        """Extract text body from email"""
        body = ''
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Skip attachments
                if 'attachment' in content_disposition:
                    continue
                
                if content_type == 'text/plain':
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
                    except:
                        pass
                elif content_type == 'text/html' and not body:
                    try:
                        html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        # Convert HTML to text (simple version)
                        import re
                        body = re.sub('<[^<]+?>', '', html)
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
            except:
                body = str(msg.get_payload())
        
        return body
    
    def process_replies(self, emails):
        """Process fetched emails as replies to outreach"""
        sequencer = EmailSequencer()
        processed = 0
        
        for email_data in emails:
            from_address = email_data['from_address']
            
            # Skip emails from yourself
            if from_address.lower() == self.username.lower():
                continue
            
            # Look for matching outbound email
            # Try to match by In-Reply-To or by sender email
            matching_email = None
            
            if email_data['in_reply_to']:
                # Match by Message-ID
                try:
                    matching_email = OutreachEmail.objects.filter(
                        message_id=email_data['in_reply_to'],
                        status='sent'
                    ).first()
                except:
                    pass
            
            if not matching_email:
                # Match by sender email (most recent sent email to this contact)
                try:
                    matching_email = OutreachEmail.objects.filter(
                        contact__email__iexact=from_address,
                        status='sent'
                    ).order_by('-sent_at').first()
                except:
                    pass
            
            if matching_email:
                # Process as reply
                should_escalate, reason = sequencer.process_reply(
                    matching_email,
                    email_data['body'],
                    timezone.now()
                )
                
                logger.info(f"Processed reply from {from_address}: escalated={should_escalate}")
                processed += 1
                
                # Mark email as processed (you could move to a folder here)
                # self.mark_processed(email_data['msg_id'])
            else:
                logger.warning(f"No matching outbound email for reply from {from_address}")
        
        return processed
    
    def mark_processed(self, msg_id, target_folder='Processed'):
        """Move processed email to target folder"""
        try:
            # Create folder if not exists
            self.connection.create(target_folder)
        except:
            pass
        
        try:
            # Copy to target folder
            self.connection.copy(msg_id, target_folder)
            # Mark for deletion
            self.connection.store(msg_id, '+FLAGS', '\\Deleted')
            self.connection.expunge()
        except Exception as e:
            logger.error(f"Error moving email {msg_id}: {e}")


def poll_inbox():
    """
    Poll inbox for replies - intended to be run as Celery task
    Run every 15 minutes
    """
    logger.info("Starting inbox poll...")
    
    receiver = IMAPReceiver()
    
    try:
        # Fetch unread messages
        emails = receiver.fetch_unread(limit=50)
        logger.info(f"Fetched {len(emails)} unread messages")
        
        if emails:
            # Process replies
            processed = receiver.process_replies(emails)
            logger.info(f"Processed {processed} replies")
        
    except Exception as e:
        logger.error(f"Error during inbox poll: {e}")
    
    finally:
        receiver.disconnect()
    
    logger.info("Inbox poll complete")
