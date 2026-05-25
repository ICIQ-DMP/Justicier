import argparse
import smtplib
from email.mime.text import MIMEText

from data import unparse_date
from logger import get_logger
from secret import read_secret

log = get_logger(__name__)


def send_mail(
    to_email: str,
    subject: str,
    body: str,
    from_email: str,
    username: str,
    password: str,
    server: str,
    port: int,
) -> None:
    # Create message
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    # Connect to Microsoft 365 SMTP
    with smtplib.SMTP(server, port) as socket:
        socket.ehlo()
        socket.starttls()  # Upgrade connection to TLS
        socket.login(username, password)
        socket.sendmail(from_email, [to_email], msg.as_string())


def build_mail_body(result_link: str, log_link: str, args: argparse.Namespace) -> str:
    """Builds the body of the email to send to the user."""
    return (
        f"Hola!\n"
        f"\n"
        f'T\'informo que la petició que vas fer al Justicier amb títol "{args.title}" i ID {args.request} per'
        f' a l\'empleat amb nom "{args.name}" des del {unparse_date(args.begin)} fins al {unparse_date(args.end)} '
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
        f"Aquest missatge ha estat auto-generat."
    )


def mail_process(result_link: str, log_link: str, args: argparse.Namespace) -> None:
    smtp_password = read_secret("SMTP_PASSWORD")
    smtp_user = read_secret("SMTP_USERNAME")
    smtp_server = read_secret("SMTP_SERVER")
    smtp_port = read_secret("SMTP_PORT")

    log.trace(f'user is: "{smtp_user}"')
    log.trace(f'pass is: "{smtp_password}"')
    log.trace(f'server is: "{smtp_server}"')
    log.trace(f'port is: "{smtp_port}"')
    log.trace(f'recipient is: "{args.author_email}"')

    subject = f'Justicier - La petició "{args.title}" amb ID {args.request} ha estat completada amb èxit'
    body = build_mail_body(result_link, log_link, args)

    send_mail(
        args.author_email,
        subject,
        body,
        smtp_user,
        smtp_user,
        smtp_password,
        smtp_server,
        int(smtp_port),
    )

    log.info("Email sent. Process complete.")
