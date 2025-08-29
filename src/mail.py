import smtplib
from email.mime.text import MIMEText
import argparse

from secret import read_secret
from data import unparse_date


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


def mail_process(result_link, log_link, args):
    smtp_password = read_secret("SMTP_PASSWORD")
    smtp_user = read_secret("SMTP_USERNAME")
    subject = f"Justicier - La petició \"{args.title}\" amb ID {str(args.request)} ha estat completada amb èxit"
    body = ("Hola!\n"
            f"\n"
            f"T'informo que la petició que vas fer al Justicier amb títol \"{args.title}\" i ID {str(args.request)} per"
            f" a l'empleat amb nom \"{args.name}\" des del {unparse_date(args.begin)} fins al {unparse_date(args.end)} "
            f"ja ha sigut resolta.\n"
            f"\n"
            f"Et deixo aquí els resultats:\n"
            f"\n"
            f"* Carpeta Sharepoint amb els documents (inclou resum a l'arrel de la carpeta): {result_link}.\n"
            f"* Fitxer de logs (només administradors): {log_link}.\n"
            f"\n"
            f"Per a qualsevol dubte o problema contacteu al Product Owner del Justicier, el Carles de la Cuadra"
            f" (cdelacuadra@iciq.es).\n"
            f"\n"
            f"Seguim,\n"
            f"\n"
            f"\n"
            f"Aleix (Avatar Digital)\n"
            f"\n"
            f"Aquest missatge ha estat auto-generat.")

    send_mail(args.author,
              subject,
              body,
              smtp_user,
              smtp_user,
              smtp_password)

    print("Email sent. Process complete. ")

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