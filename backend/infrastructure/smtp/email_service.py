import aiosmtplib
from email.message import EmailMessage
from core.config import settings
import os
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
            <p>This OTP is valid for 10 minutes. Do not share it with anyone.</p>
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
    
    threat_level = ai_decision.get('threat_class', 'Unknown')
    confidence = (ai_decision.get('confidence', ai_decision.get('score', 0)) * 100)
    
    body = f"""
    <html>
      <head>
        <style>
          body {{ font-family: 'Inter', -apple-system, sans-serif; background-color: #0f111a; color: #e2e8f0; margin: 0; padding: 20px; }}
          .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(145deg, #1e2130 0%, #151722 100%); border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); padding: 40px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }}
          .header {{ display: flex; align-items: center; justify-content: center; margin-bottom: 30px; }}
          .title {{ color: #a78bfa; font-size: 24px; font-weight: 700; text-align: center; margin: 0; }}
          .case-box {{ background: rgba(0,0,0,0.3); border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid rgba(167, 139, 250, 0.2); }}
          .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; margin-bottom: 4px; display: block; }}
          .value {{ font-size: 18px; color: #f8fafc; font-weight: 600; margin: 0 0 15px 0; }}
          .value:last-child {{ margin-bottom: 0; }}
          .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; color: #64748b; }}
          .highlight {{ color: #10b981; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2 class="title">🛡️ Digital Rakshak</h2>
          </div>
          <p style="text-align: center; font-size: 16px; line-height: 1.6;">Thank you for your report. Your cybercrime case has been securely registered in the National Database.</p>
          
          <div class="case-box">
            <span class="label">Case Number</span>
            <p class="value">{case_number}</p>
            
            <span class="label">AI Assessed Threat Level</span>
            <p class="value" style="color: #fbbf24;">{threat_level}</p>
            
            <span class="label">Analysis Confidence</span>
            <p class="value highlight">{confidence:.1f}%</p>
          </div>
          
          <p style="text-align: center; font-size: 14px; line-height: 1.6; color: #cbd5e1;">Our cyber analysts and partner law enforcement agencies are actively reviewing the details. You can track live updates directly on your dashboard.</p>
          
          <div class="footer">
            This is an automated encrypted message. Please do not reply.
          </div>
        </div>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_admin_case_notification_email(admin_email: str, case_number: str, threat_level: str) -> bool:
    subject = f"🚨 ALERT: New Case #{case_number}"
    
    body = f"""
    <html>
      <head>
        <style>
          body {{ font-family: 'Inter', -apple-system, sans-serif; background-color: #0f111a; color: #e2e8f0; margin: 0; padding: 20px; }}
          .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(145deg, #2a161b 0%, #1a0f12 100%); border-radius: 16px; border: 1px solid rgba(244, 63, 94, 0.2); padding: 40px; box-shadow: 0 25px 50px -12px rgba(244, 63, 94, 0.15); }}
          .header {{ text-align: center; margin-bottom: 30px; }}
          .title {{ color: #f43f5e; font-size: 24px; font-weight: 700; margin: 0; display: flex; align-items: center; justify-content: center; gap: 10px; }}
          .case-box {{ background: rgba(0,0,0,0.4); border-radius: 12px; padding: 20px; margin: 20px 0; border: 1px solid rgba(244, 63, 94, 0.1); }}
          .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #fda4af; margin-bottom: 4px; display: block; }}
          .value {{ font-size: 18px; color: #fff; font-weight: 600; margin: 0 0 15px 0; }}
          .value:last-child {{ margin-bottom: 0; }}
          .btn {{ display: inline-block; background: #f43f5e; color: #fff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; margin-top: 10px; text-align: center; width: calc(100% - 48px); }}
          .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(244, 63, 94, 0.1); font-size: 12px; color: #94a3b8; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h2 class="title">⚠️ Critical Review Required</h2>
          </div>
          <p style="text-align: center; font-size: 16px; line-height: 1.6;">A new high-priority cybercrime case has just been submitted to the platform and requires immediate assignment.</p>
          
          <div class="case-box">
            <span class="label">Case Number</span>
            <p class="value">{case_number}</p>
            
            <span class="label">AI Assessed Threat Level</span>
            <p class="value" style="color: #fbbf24;">{threat_level}</p>
          </div>
          
          <a href="{os.getenv('PLATFORM_URL', 'http://localhost:3000')}/admin/workbench" class="btn">Open Admin Workbench</a>
          
          <div class="footer">
            Digital Rakshak Automated Orchestration System
          </div>
        </div>
      </body>
    </html>
    """
    return await send_email(admin_email, subject, body, is_html=True)

async def send_account_created_email(to_email: str, full_name: str, role: str, temp_password: str) -> bool:
    subject = "Welcome to Digital Rakshak - Your Account is Ready"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4f46e5;">Welcome, {full_name or 'User'}!</h2>
        <p>An administrator has created a <strong>{role}</strong> account for you on the Digital Rakshak platform.</p>
        <p>You can now log in using the following credentials:</p>
        <ul>
            <li><strong>Email:</strong> {to_email}</li>
            <li><strong>Temporary Password:</strong> {temp_password}</li>
        </ul>
        <p><em>For your security, we strongly recommend changing your password immediately after logging in.</em></p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message from the Digital Rakshak Orchestration System.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_account_deleted_email(to_email: str, full_name: str) -> bool:
    subject = "Digital Rakshak - Account Access Revoked"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Notice of Account Deletion</h2>
        <p>Dear {full_name or 'User'},</p>
        <p>This email is to notify you that your access to the Digital Rakshak platform has been revoked and your account has been permanently deleted by a system administrator.</p>
        <p>If you believe this was in error, please contact your commanding officer or platform administrator.</p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message. Please do not reply.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_password_reset_otp_email(to_email: str, otp: str):
    subject = "Digital Rakshak - Password Reset OTP"
    body = f"""
    <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>We received a request to reset the password for your Digital Rakshak account.</p>
            <p>Your One-Time Password (OTP) for resetting your password is: <strong>{otp}</strong></p>
            <p>This OTP is valid for 10 minutes. If you did not request a password reset, please ignore this email and your password will remain unchanged.</p>
        </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_case_assigned_victim_email(to_email: str, case_number: str) -> bool:
    subject = f"Digital Rakshak - Update on Case #{case_number}"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #4f46e5;">Case Assigned</h2>
        <p>Your cybercrime report (Case #{case_number}) has been assigned to a police station by the admin.</p>
        <p>The concerned official will shortly contact you on the phone number you provided.</p>
        <p>You can track the progress on your Citizen Dashboard.</p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message. Please do not reply.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_case_assigned_investigator_email(to_email: str, case_number: str) -> bool:
    subject = f"ACTION REQUIRED: New Case Assigned #{case_number}"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #f43f5e;">New Case Assignment</h2>
        <p>You have been assigned a new cybercrime case (Case #{case_number}) by the platform administrator.</p>
        <p>Please log in to your Investigator Dashboard to review the victim's details, analyze the evidence, and accept the case to begin the investigation.</p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message. Please do not reply.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)

async def send_case_accepted_admin_email(to_email: str, case_number: str, investigator_name: str) -> bool:
    subject = f"Case #{case_number} - Investigation Started"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Case Accepted</h2>
        <p>Case #{case_number} has been officially accepted by Investigator <strong>{investigator_name}</strong>.</p>
        <p>The global case status has been updated to INVESTIGATING.</p>
        <hr />
        <p style="font-size: 12px; color: #888;">This is an automated message. Please do not reply.</p>
      </body>
    </html>
    """
    return await send_email(to_email, subject, body, is_html=True)
