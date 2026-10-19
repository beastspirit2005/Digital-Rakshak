import aiosmtplib
from typing import Optional, List, Dict, Any
from email.message import EmailMessage
from core.config import settings
from datetime import datetime, timezone
import os
import logging

logger = logging.getLogger(__name__)

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    is_html: bool = False,
    attachments: list = None,
    reply_to: str = None,
):
    message = EmailMessage()
    from_name = (settings.SMTP_FROM_NAME or "Digital Rakshak").strip('"').strip("'")
    from_email = settings.SMTP_FROM_EMAIL

    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message["Reply-To"] = reply_to or f"{from_name} Support <{from_email}>"
    
    if is_html:
        message.set_content("Please view this email in an HTML-compatible client.")
        message.add_alternative(body, subtype='html')
    else:
        message.set_content(body)

    if attachments:
        for att in attachments:
            try:
                data = att.get("data")
                if isinstance(data, str):
                    data = data.encode("utf-8")
                maintype = att.get("maintype", "application")
                subtype = att.get("subtype", "octet-stream")
                filename = att.get("filename", "attachment.dat")
                message.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
            except Exception as att_err:
                logger.error(f"Failed to attach file {att.get('filename')}: {att_err}")
    
    try:
        response = await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=False,
            start_tls=True,
            timeout=20
        )
        logger.info(f"Email sent successfully to {to_email}: {response}")
        return True
    except aiosmtplib.errors.SMTPAuthenticationError as auth_err:
        logger.error(f"SMTP Authentication failed for {settings.SMTP_USER}: {auth_err}")
        return False
    except aiosmtplib.errors.SMTPTimeoutError as timeout_err:
        logger.error(f"SMTP Timeout connecting to {settings.SMTP_HOST}:{settings.SMTP_PORT}: {timeout_err}")
        return False
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
    subject = "Welcome to Digital Rakshak — National Cyber Defense Core"
    role_display = "Citizen Defense Shield" if role == "citizen" else role.replace("_", " ").title()
    body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
    .card {{ max-width: 620px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
    .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding: 36px 28px; text-align: center; border-bottom: 1px solid #1e293b; }}
    .badge {{ display: inline-block; padding: 4px 12px; background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; border-radius: 9999px; color: #60a5fa; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
    .title {{ font-size: 24px; font-weight: 800; color: #ffffff; margin: 0 0 6px 0; }}
    .subtitle {{ font-size: 13px; color: #94a3b8; margin: 0; }}
    .content {{ padding: 28px; }}
    .welcome-text {{ font-size: 14px; color: #cbd5e1; line-height: 1.6; margin-bottom: 24px; }}
    .feature-box {{ background: #0b101e; border: 1px solid #1e293b; border-radius: 12px; padding: 18px 20px; margin-bottom: 24px; }}
    .feature-item {{ margin-bottom: 14px; }}
    .feature-item:last-child {{ margin-bottom: 0; }}
    .feature-title {{ font-weight: 700; font-size: 13px; color: #38bdf8; margin-bottom: 2px; }}
    .feature-desc {{ font-size: 12px; color: #94a3b8; line-height: 1.4; }}
    .btn-container {{ text-align: center; margin: 28px 0 16px 0; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: #ffffff !important; text-decoration: none; font-weight: 700; font-size: 14px; padding: 14px 28px; border-radius: 10px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4); }}
    .footer {{ background: #0b0f19; padding: 20px 28px; text-align: center; border-top: 1px solid #1e293b; font-size: 11px; color: #64748b; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="badge">National Cyber Defense Core Active</div>
      <h1 class="title">Welcome to Digital Rakshak</h1>
      <p class="subtitle">Your shield against zero-day cyber scams and digital financial fraud</p>
    </div>
    <div class="content">
      <p class="welcome-text">
        Dear <strong>{full_name or 'Valued Citizen'}</strong>,<br><br>
        Welcome to India's unified real-time cyber defense network. Your account has been initialized with active role: <strong>{role_display}</strong>.
      </p>

      <div class="feature-box">
        <div class="feature-item">
          <div class="feature-title">&#128269; Zero-Day Threat Analyzer</div>
          <div class="feature-desc">Scan suspicious URLs, SMS texts, UPI IDs, QR codes, and phone numbers before interacting with them.</div>
        </div>
        <div class="feature-item">
          <div class="feature-title">&#9889; Attack DNA Correlation</div>
          <div class="feature-desc">Real-time matching against 1.2M+ active Indian scam syndicates and banking mule networks.</div>
        </div>
        <div class="feature-item">
          <div class="feature-title">&#127963; 1-Click Nodal Escalation</div>
          <div class="feature-desc">Immediate incident reporting with automated SHA-256 evidence vaults and police/bank coordination.</div>
        </div>
      </div>

      <div class="btn-container">
        <a href="http://localhost:3000/personal" class="btn">Launch Protection Portal &rarr;</a>
      </div>
    </div>
    <div class="footer">
      Digital Rakshak Cyber Defense &bull; National Threat Intelligence Network<br>
      This is an automated system-generated electronic welcome confirmation.
    </div>
  </div>
</body>
</html>"""
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


async def send_subscription_confirmed_email(
    to_email: str,
    full_name: str,
    plan_name: str,
    subscription_id: str,
    base_amount: float,
    cgst_amount: float,
    sgst_amount: float,
    tax_amount: float,
    gross_amount: float,
    billing_cycle: str,
    invoice_number: str,
    invoice_html: str = "",
    invoice_pdf_bytes: Optional[bytes] = None,
) -> bool:
    subject = f"Digital Rakshak Pro Activated - Tax Invoice #{invoice_number}"
    invoice_filename = f"Digital_Rakshak_Tax_Invoice_{subscription_id}.pdf"

    if invoice_pdf_bytes is None:
        try:
            from infrastructure.pdf.invoice_pdf import generate_invoice_pdf
            invoice_pdf_bytes = generate_invoice_pdf(
                invoice_number=invoice_number,
                invoice_date=datetime.now(timezone.utc).strftime("%d-%b-%Y"),
                buyer_name=full_name or "Valued Citizen",
                buyer_email=to_email,
                plan_name=plan_name,
                taxable_base=base_amount,
                cgst=cgst_amount,
                sgst=sgst_amount,
                total_tax=tax_amount,
                gross_amount=gross_amount,
            )
        except Exception as pdf_err:
            logger.warning(f"Could not generate invoice PDF on the fly: {pdf_err}")

    body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
    .card {{ max-width: 620px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
    .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding: 32px 28px; text-align: center; border-bottom: 1px solid #1e293b; }}
    .badge {{ display: inline-block; padding: 4px 12px; background: rgba(59, 130, 246, 0.2); border: 1px solid #3b82f6; border-radius: 9999px; color: #60a5fa; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
    .title {{ font-size: 24px; font-weight: 800; color: #ffffff; margin: 0 0 6px 0; }}
    .subtitle {{ font-size: 13px; color: #94a3b8; margin: 0; }}
    .content {{ padding: 28px; }}
    .welcome-text {{ font-size: 14px; color: #cbd5e1; line-height: 1.6; margin-bottom: 24px; }}
    .table-container {{ background: #0b101e; border: 1px solid #1e293b; border-radius: 12px; overflow: hidden; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #111827; padding: 12px 16px; text-align: left; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid #1e293b; }}
    td {{ padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #e2e8f0; }}
    tr:last-child td {{ border-bottom: none; }}
    .total-row td {{ font-weight: 800; font-size: 15px; color: #38bdf8; background: #0f172a; }}
    .tax-badge {{ font-size: 10px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 2px 6px; border-radius: 4px; margin-left: 6px; }}
    .attachment-notice {{ background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 10px; padding: 14px 18px; margin-top: 20px; font-size: 12px; color: #34d399; line-height: 1.5; }}
    .btn-container {{ text-align: center; margin: 24px 0 12px 0; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #ffffff !important; text-decoration: none; font-weight: 700; font-size: 13px; padding: 12px 24px; border-radius: 8px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3); }}
    .footer {{ background: #0b0f19; padding: 20px 28px; text-align: center; border-top: 1px solid #1e293b; font-size: 11px; color: #64748b; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="badge">Shield Level: National Pro Active</div>
      <h1 class="title">Welcome to Digital Rakshak Pro</h1>
      <p class="subtitle">Payment verified successfully &bull; Invoice #{invoice_number}</p>
    </div>
    <div class="content">
      <p class="welcome-text">
        Dear <strong>{full_name or 'Valued Citizen'}</strong>,<br><br>
        Thank you for upgrading to <strong>{plan_name}</strong>. Your account has been equipped with full Zero-Day Threat Core detection, National Threat Pattern Registry (TPR) correlation, and priority attack DNA lookup.
      </p>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Description / SAC 998313</th>
              <th style="text-align: right;">Amount (INR)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{plan_name} Base Subscription ({billing_cycle})</td>
              <td style="text-align: right; font-weight: 600;">&#8377;{base_amount:.2f}</td>
            </tr>
            <tr>
              <td>Central GST (CGST @ 9.0%) <span class="tax-badge">Govt Tax</span></td>
              <td style="text-align: right;">&#8377;{cgst_amount:.2f}</td>
            </tr>
            <tr>
              <td>State GST (SGST @ 9.0%) <span class="tax-badge">Govt Tax</span></td>
              <td style="text-align: right;">&#8377;{sgst_amount:.2f}</td>
            </tr>
            <tr>
              <td>Total 18% GST (Non-refundable statutory tax)</td>
              <td style="text-align: right; font-weight: 600;">&#8377;{tax_amount:.2f}</td>
            </tr>
            <tr class="total-row">
              <td>Total Paid (Inclusive of 18% GST)</td>
              <td style="text-align: right;">&#8377;{gross_amount:.2f}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="attachment-notice">
        <strong>&#128206; Mobile-Compatible Tax Invoice Attached (PDF):</strong><br>
        Your official GST-compliant Tax Invoice (<code>{invoice_filename}</code>) is attached directly to this email in standard PDF format. Tap to open and view immediately on your phone (iPhone/Android) or laptop.
      </div>

      <div class="btn-container">
        <a href="http://localhost:8000/v1/billing/invoice/{subscription_id}/pdf" class="btn">&#128196; Download PDF Tax Invoice</a>
      </div>
    </div>
    <div class="footer">
      Digital Rakshak Cyber Defense &bull; National Threat Intelligence Network<br>
      GSTIN: 07AABCD1234E1Z5 &bull; SAC Code: 998313 &bull; System-generated electronic confirmation.
    </div>
  </div>
</body>
</html>"""

    attachments = []
    if invoice_pdf_bytes:
        attachments.append({
            "data": invoice_pdf_bytes,
            "filename": invoice_filename,
            "maintype": "application",
            "subtype": "pdf",
        })
    elif invoice_html:
        attachments.append({
            "data": invoice_html,
            "filename": f"Digital_Rakshak_Tax_Invoice_{subscription_id}.html",
            "maintype": "text",
            "subtype": "html",
        })

    return await send_email(
        to_email=to_email,
        subject=subject,
        body=body,
        is_html=True,
        attachments=attachments,
    )


async def send_subscription_canceled_email(
    to_email: str,
    full_name: str,
    plan_name: str,
    subscription_id: str,
    original_base_amount: float,
    tax_amount: float,
    gross_amount: float,
    start_date: str,
    cancel_date: str,
    days_used: int,
    total_days: int,
    deduction_amount: float,
    refund_amount: float,
    refund_timeline: str = "5-7 business days",
) -> bool:
    subject = "Digital Rakshak Pro Subscription Canceled - Prorated Refund Details"

    body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
    .card {{ max-width: 620px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
    .header {{ background: linear-gradient(135deg, #881337 0%, #0f172a 100%); padding: 32px 28px; text-align: center; border-bottom: 1px solid #1e293b; }}
    .badge {{ display: inline-block; padding: 4px 12px; background: rgba(244, 63, 94, 0.2); border: 1px solid #f43f5e; border-radius: 9999px; color: #fb7185; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }}
    .title {{ font-size: 24px; font-weight: 800; color: #ffffff; margin: 0 0 6px 0; }}
    .subtitle {{ font-size: 13px; color: #94a3b8; margin: 0; }}
    .content {{ padding: 28px; }}
    .notice-text {{ font-size: 14px; color: #cbd5e1; line-height: 1.6; margin-bottom: 24px; }}
    .table-container {{ background: #0b101e; border: 1px solid #1e293b; border-radius: 12px; overflow: hidden; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #111827; padding: 12px 16px; text-align: left; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid #1e293b; }}
    td {{ padding: 12px 16px; border-bottom: 1px solid #1e293b; color: #e2e8f0; }}
    tr:last-child td {{ border-bottom: none; }}
    .refund-row td {{ font-weight: 800; font-size: 15px; color: #34d399; background: #064e3b22; border-top: 1px solid #059669; }}
    .tax-retained td {{ font-size: 12px; color: #94a3b8; background: #0f172a; }}
    .policy-box {{ background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 10px; padding: 14px 18px; margin-bottom: 20px; font-size: 12px; color: #fbbf24; line-height: 1.5; }}
    .free-tier-box {{ background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 10px; padding: 14px 18px; margin-bottom: 20px; font-size: 12px; color: #93c5fd; line-height: 1.5; }}
    .footer {{ background: #0b0f19; padding: 20px 28px; text-align: center; border-top: 1px solid #1e293b; font-size: 11px; color: #64748b; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <div class="badge">Subscription Canceled</div>
      <h1 class="title">Digital Rakshak Pro Canceled</h1>
      <p class="subtitle">Effective Date: {cancel_date} &bull; Ref #{subscription_id[:16] if subscription_id else 'SUB-REC'}</p>
    </div>
    <div class="content">
      <p class="notice-text">
        Dear <strong>{full_name or 'Valued Citizen'}</strong>,<br><br>
        Your subscription for <strong>{plan_name}</strong> has been canceled as requested. Any active recurring e-mandate on your account has been terminated immediately.
      </p>

      <div class="policy-box">
        <strong>Tax &amp; Prorated Refund Policy:</strong><br>
        In accordance with statutory GST guidelines and platform terms, <strong>18% Government GST (SAC 998313) remitted to the government is strictly non-refundable</strong>. Your refund is calculated strictly on the unutilized portion of the base subscription fee based on active days used.
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Prorated Refund Calculation Breakdown</th>
              <th style="text-align: right;">Amount (INR)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Original Base Subscription Fee</td>
              <td style="text-align: right; font-weight: 600;">&#8377;{original_base_amount:.2f}</td>
            </tr>
            <tr>
              <td>Total Billing Period Duration</td>
              <td style="text-align: right;">{total_days} Days</td>
            </tr>
            <tr>
              <td>Active Defense Duration Utilized</td>
              <td style="text-align: right;">{days_used} Days</td>
            </tr>
            <tr>
              <td>Base Usage Deduction ({days_used} of {total_days} days)</td>
              <td style="text-align: right; color: #f87171;">-&#8377;{deduction_amount:.2f}</td>
            </tr>
            <tr class="refund-row">
              <td>Net Prorated Base Refund Initiated</td>
              <td style="text-align: right;">&#8377;{refund_amount:.2f}</td>
            </tr>
            <tr class="tax-retained">
              <td>18% Statutory GST Paid (Non-refundable remittance)</td>
              <td style="text-align: right;">&#8377;{tax_amount:.2f} (Retained)</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="free-tier-box">
        <strong>Zero Data Loss &bull; Free Shield Continues:</strong><br>
        Your account remains active on the <strong>Free Shield</strong> plan. All your past scan records, downloaded reports, and evidence remain safely saved in your account. You can still perform on-demand URL, SMS, UPI, and phone scans at any time.
      </div>

      <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin: 0;">
        <strong>Refund Settlement:</strong> Your refund of <strong>&#8377;{refund_amount:.2f}</strong> has been initiated and will credit back to your original payment method (UPI / Card) within <strong>{refund_timeline}</strong> per RBI guidelines.
      </p>
    </div>
    <div class="footer">
      Digital Rakshak Cyber Defense &bull; National Threat Intelligence Network<br>
      Note: No bill or invoice is attached to this cancellation notice.
    </div>
  </div>
</body>
</html>"""

    # Strictly NO attachments for cancellation email
    return await send_email(
        to_email=to_email,
        subject=subject,
        body=body,
        is_html=True,
        attachments=None,
    )
