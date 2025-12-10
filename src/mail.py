import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
import argparse

from secret import read_secret
from data import unparse_date


def send_mail2(username, password, to, host, port, subject, content):
    SMTP_SERVER = host
    SMTP_PORT = port
    USERNAME = username
    PASSWORD = password

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = USERNAME
    msg["To"] = to
    msg.set_content(content)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()  # Use TLS
        smtp.login(USERNAME, PASSWORD)
        smtp.send_message(msg)

    print("Email sent successfully!")


def send_mail(to_email, subject, body, from_email, username, password, server: str, port: int):
    # Create message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Connect to Microsoft 365 SMTP
    with smtplib.SMTP(server, port) as server:
        server.ehlo()
        server.starttls()              # Upgrade connection to TLS
        server.login(username, password)
        server.sendmail(from_email, [to_email], msg.as_string())


def mail_process(result_link, log_link, args):
    smtp_password = read_secret("SMTP_PASSWORD")
    smtp_user = read_secret("SMTP_USERNAME")
    smtp_server = read_secret("SMTP_SERVER")
    smtp_port = read_secret("SMTP_PORT")

    #print("user is: \"" + str(smtp_user) + "\"")
    #print("pass is: \"" + str(smtp_password) + "\"")
    #print("server is: \"" + str(smtp_server) + "\"")
    #print("port is: \"" + str(smtp_port) + "\"")
    #print("recipient is: \"" + str(args.author_email) + "\"")

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

    send_mail(args.author_email,
              subject,
              body,
              smtp_user,
              smtp_user,
              smtp_password,
              smtp_server,
              smtp_port)

    print("Email sent. Process complete. ")

if __name__ == "__main__":
    print("Start program")
    parser = argparse.ArgumentParser()
    parser.add_argument("--author", required=True, help="Recipient email")
    args = parser.parse_args()

    '''
    print("Sending email")
    print("Author: " + args.author)
    print("username: " + read_secret("SMTP_USERNAME"))
    print("password: " + read_secret("SMTP_PASSWORD"))
    print("port: " + read_secret("SMTP_PORT"))
    print("Server: " + read_secret("SMTP_SERVER"))
    send_mail2(
        to=args.author,
        subject="test from Justicier",
        content="Hello, this is a test email sent using Office 365 SMTP.",
        username=read_secret("SMTP_USERNAME"),
        password=read_secret("SMTP_PASSWORD"),
        port=read_secret("SMTP_PORT"),
        host=read_secret("SMTP_SERVER"),
    )
    '''

    print("Sending email with another func")
    print("To: " + args.author)
    print("username: " + read_secret("SMTP_USERNAME"))
    print("password: " + read_secret("SMTP_PASSWORD"))
    print("port: " + read_secret("SMTP_PORT"))
    print("Server: " + read_secret("SMTP_SERVER"))
    send_mail(
        to_email=args.author,
        subject="test email",
        body="a test of email",
        from_email=read_secret("SMTP_USERNAME"),
        username=read_secret("SMTP_USERNAME"),
        password=read_secret("SMTP_PASSWORD"),
        server=read_secret("SMTP_SERVER"),
        port=read_secret("SMTP_PORT")
    )
