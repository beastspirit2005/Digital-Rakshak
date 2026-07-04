import aiosmtplib
from email.message import EmailMessage
from core.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message["Subject"] = subject
    
    if is_html:
        message.add_alternative(body, subtype='html')
    else:
        message.set_content(body)
    
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=False,
            start_tls=True,
        )
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False

async def send_otp_email(to_email: str, otp: str):
    subject = "Digital Rakshak - Your Login OTP"
    body = f"""
    <html>
        <body>
            <h2>Welcome to Digital Rakshak</h2>
            <p>Your One-Time Password (OTP) for login is: <strong>{otp}</strong></p>
            <p>This OTP is valid for 5 minutes. Do not share it with anyone.</p>
        </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_approval_pending_email(to_email: str, role: str):
    subject = "Digital Rakshak - Account Pending Approval"
    body = f"""
    <html>
        <body>
            <h2>Account Registration Received</h2>
            <p>Your registration for the role of <strong>{role}</strong> has been received and is pending admin approval.</p>
            <p>You will be notified once your account is approved.</p>
        </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_welcome_email(to_email: str, full_name: str, role: str) -> bool:
    subject = "Welcome to Digital Rakshak!"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4f46e5;">Welcome to Digital Rakshak, {full_name or 'User'}!</h2>
        <p>Your account has been successfully approved and activated.</p>
        <p><strong>Assigned Role:</strong> {role}</p>
        <p>You can now log in and access your dashboard.</p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message. Please do not reply.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_case_confirmation_email(to_email: str, case_number: str, ai_decision: dict) -> bool:
    subject = f"Report Received - Case #{case_number}"
    
    threat_level = ai_decision.get('decision', 'Under Review')
    confidence = (ai_decision.get('score', 0) * 100)
    
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4f46e5;">Your Report Has Been Submitted</h2>
        <p>Thank you for reporting to Digital Rakshak. Your case has been registered successfully.</p>
        <p><strong>Case Number:</strong> {case_number}</p>
        <p><strong>Initial AI Threat Level:</strong> {threat_level} (Confidence: {confidence:.1f}%)</p>
        <p>Our cyber analysts and partner agencies are reviewing the details. You can track the status on your dashboard.</p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message. Please do not reply.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)
