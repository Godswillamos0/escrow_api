from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from core.config import (ZOHO_EMAIL, ZOHO_SMTP_PASSWORD, ZOHO_SMTP_PORT, ZOHO_SMTP_HOST)
 

conf = ConnectionConfig(
    MAIL_USERNAME=ZOHO_EMAIL,
    MAIL_PASSWORD=ZOHO_SMTP_PASSWORD,
    MAIL_FROM=ZOHO_EMAIL,
    MAIL_PORT=ZOHO_SMTP_PORT,
    MAIL_SERVER=ZOHO_SMTP_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

# use in a route
from fastapi import FastAPI #, BackgroundTasks
app = FastAPI()


async def send_mail( email: str, subject: str, body: str): #background_tasks: BackgroundTasks,
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype=MessageType.plain
    )

    fm = FastMail(conf)
    await fm.send_message(message)
    