import smtplib
from email.mime.text import MIMEText
import argparse


def send_mail(to_email, subject, body, from_email, username, password):
    # Create message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Connect to Microsoft 365 SMTP
    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.ehlo()
        server.starttls()              # Upgrade connection to TLS
        server.login(username, password)
        server.sendmail(from_email, [to_email], msg.as_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--author", required=True, help="Recipient email")
    args = parser.parse_args()

    send_mail(
        to_email=args.author,
        subject="Test email from Python",
        body="Hello, this is a test email sent using Office 365 SMTP.",
        from_email="you@yourdomain.com",
        username="you@yourdomain.com",
        password="YOUR_PASSWORD_OR_APP_PASSWORD"
    )