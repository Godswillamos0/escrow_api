import os
from dotenv import load_dotenv

load_dotenv()

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_...")
PAYSTACK_BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co")


SQL_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
#DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")



## Email Configuration
ZOHO_EMAIL = os.getenv("ZOHO_MAIL")
ZOHO_SMTP_PASSWORD = os.getenv("ZOHO_PASSWORD")
ZOHO_SMTP_PORT = int(os.getenv("ZOHO_SMTP_PORT", 587))
ZOHO_SMTP_HOST = os.getenv("ZOHO_SMTP_HOST", "smtp.zoho.com")

MAIL_TLS = True
MAIL_SSL = False
USE_CREDENTIALS = True
VALIDATE_CERTS = True
