import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@box5.com")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def send_email(to: str, subject: str, html_body: str, text_body: str = "") -> bool:
    if not SMTP_HOST or not SMTP_USER:
        print(f"[EMAIL MOCK] To: {to}, Subject: {subject}")
        print(f"  Body: {html_body[:200]}...")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def send_verification_email(email: str, username: str, token: str) -> bool:
    verify_url = f"{BASE_URL}/verify-email?token={token}"
    subject = "Verify your box5 email"
    html = f"""
    <h1>Welcome to box5, {username}!</h1>
    <p>Please click the link below to verify your email address:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>This link expires in 24 hours.</p>
    """
    text = f"Welcome to box5, {username}!\n\nPlease visit: {verify_url}\n\nThis link expires in 24 hours."
    return send_email(email, subject, html, text)


def send_password_reset_email(email: str, username: str, token: str) -> bool:
    reset_url = f"{BASE_URL}/reset-password?token={token}"
    subject = "Reset your box5 password"
    html = f"""
    <h1>Password Reset, {username}</h1>
    <p>Click the link below to reset your password:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>This link expires in 1 hour. If you did not request this, please ignore this email.</p>
    """
    text = f"Password Reset\n\nVisit: {reset_url}\n\nThis link expires in 1 hour."
    return send_email(email, subject, html, text)