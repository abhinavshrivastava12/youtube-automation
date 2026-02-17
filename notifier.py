import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

def send_notification(title, video_url):
    """Send notification via email or Discord"""
    
    # Option 1: Email
    send_email_notification(title, video_url)
    
    # Option 2: Discord (if webhook URL exists)
    if os.getenv('DISCORD_WEBHOOK_URL'):
        send_discord_notification(title, video_url)

def send_email_notification(title, video_url):
    """Send email notification"""
    try:
        sender = os.getenv('EMAIL_FROM')
        password = os.getenv('EMAIL_PASSWORD')
        receiver = os.getenv('EMAIL_TO')
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = f'✅ Video Uploaded: {title}'
        
        body = f"""
        Your YouTube video has been successfully uploaded!
        
        Title: {title}
        URL: {video_url}
        
        Check it out and share with your audience!
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        
        print("✅ Email notification sent!")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def send_discord_notification(title, video_url):
    """Send Discord webhook notification"""
    try:
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        
        data = {
            "content": f"🎉 **New Video Uploaded!**\n\n**{title}**\n{video_url}"
        }
        
        requests.post(webhook_url, json=data)
        print("✅ Discord notification sent!")
    except Exception as e:
        print(f"❌ Discord notification failed: {e}")