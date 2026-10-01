import smtplib
from email.message import EmailMessage
from ..config import settings

def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False
    msg=EmailMessage()
    msg["From"]=settings.SMTP_FROM
    msg["To"]=to
    msg["Subject"]=subject
    msg.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST,settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER,settings.SMTP_PASSWORD)
        server.send_message(msg)
    return True
