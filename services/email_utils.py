from authlib.integrations.starlette_client import OAuth
from config import settings

from email.message import EmailMessage

import aiosmtplib
from fastapi.templating import Jinja2Templates

from config import settings

templates = Jinja2Templates(directory="templates")

# ====================={GOOGLE OAUTH2 CONFIGURATION}=======================
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret.get_secret_value(),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration", # Note the hyphen: openid-configuration
    client_kwargs={"scope": "openid email profile"},
)
# ===================={EMAIL SENDING FUNCTION}============================
async def send_email(
    to_email: str,
    subject: str,
    plain_text: str,
    html_content: str | None = None,
  ) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(plain_text)

    if html_content:
        message.add_alternative(html_content, subtype="html")


        ## aiosmtplib.send call
        await aiosmtplib.send(
            message,
            hostname=settings.mail_server,
            port=settings.mail_port,
            username=settings.mail_username if settings.mail_username else None,
            password=settings.mail_password.get_secret_value() or None,
            start_tls=settings.mail_use_tls,
        )
# ==================={PASSWORD RESET EMAIL FUNCTION}=======================
async def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    number_of_minutes = settings.reset_token_expire_minutes
    template = templates.env.get_template("email/password_reset.html")
    html_content = template.render(reset_url=reset_url, username=username, number_of_minutes=number_of_minutes)

    plain_text = f"""Hi {username},

  You requested to reset your password. Click the link below to set a new password:

  {reset_url}

  This link will expire in {number_of_minutes} minutes.

  If you didn't request this, you can safely ignore this email.

  Best regards,
  The Clinic webApp  Team
  """
    # print(f'email senting to {to_email}')
    await send_email(
        to_email=to_email,
        subject="Reset Your Password -  Clinic webApp",
        plain_text=plain_text,
        html_content=html_content,
    )
    # print(f'email sented to {to_email}')
# =================={EMAIL VALIDATION EMAIL FUNCTION}=======================
async def send_email_validation_email(to_email: str, username: str, token: str) -> None:
    validation_url = f"{settings.frontend_url}/api/authentication/vialidate_email/{token}"
    number_of_minutes = settings.reset_token_expire_minutes
    template = templates.env.get_template("email/email_validation.html")
    html_content = template.render(validation_url=validation_url, username=username, number_of_minutes=number_of_minutes)

    plain_text = f"""Hi {username},
    Please validate your email address by clicking the link below:

    {validation_url}

      This link will expire in {number_of_minutes} minutes.

    If you didn't create an account, you can safely ignore this email.

    If the button doesn't work, copy and paste this link into your browser:

    {validation_url}

    Best regards,
    The Clinic webApp Team
    """
    await send_email(
        to_email=to_email,
        subject="Validate Your Email - Clinic webApp",
        plain_text=plain_text,
        html_content=html_content,
    )

