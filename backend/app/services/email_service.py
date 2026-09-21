"""
Email Notification Service for विपद्Sathi (BipatSathi).

Dispatches rich HTML alert emails with photo attachments to authorities
using Gmail SMTP (bipadsathi1@gmail.com) with automatic error handling.
"""

import os
import smtplib
import mimetypes
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Defaults
DEFAULT_GMAIL_USER = "bipadsathi1@gmail.com"
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587


_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
_RECIPIENTS_FILE = os.path.join(_DATA_DIR, "alert_recipients.json")


class EmailService:
    """Service for dispatching incident and detection alert emails via Gmail SMTP."""

    def __init__(
        self,
        gmail_user: Optional[str] = None,
        app_password: Optional[str] = None,
        authority_emails: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
    ):
        self.gmail_user = gmail_user or os.getenv("GMAIL_USER", DEFAULT_GMAIL_USER).strip()
        self.app_password = app_password or os.getenv("GMAIL_APP_PASSWORD", "").strip()
        self.authority_emails_raw = authority_emails or os.getenv("AUTHORITY_EMAILS", "").strip()
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", DEFAULT_SMTP_HOST).strip()
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", str(DEFAULT_SMTP_PORT)))

    def get_recipients(self, override_emails: Optional[List[str]] = None) -> List[str]:
        """Returns the list of recipient emails, checking the persistent JSON file first."""
        if override_emails:
            return [e.strip() for e in override_emails if e.strip()]

        if os.path.isfile(_RECIPIENTS_FILE):
            try:
                import json
                with open(_RECIPIENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    return [str(e).strip() for e in data if str(e).strip()]
                elif isinstance(data, dict) and "recipients" in data:
                    return [str(e).strip() for e in data["recipients"] if str(e).strip()]
            except Exception as e:
                logger.warning(f"[EmailService] Could not read recipients file: {e}")

        raw = os.getenv("AUTHORITY_EMAILS", "").strip() or self.authority_emails_raw
        if not raw:
            return [self.gmail_user] if self.gmail_user else []
        return [e.strip() for e in raw.split(",") if e.strip()]

    def _get_recipients(self, override_emails: Optional[List[str]] = None) -> List[str]:
        return self.get_recipients(override_emails)

    def set_recipients(self, emails: List[str]) -> List[str]:
        """Saves recipient emails to data/alert_recipients.json."""
        cleaned = []
        for e in emails:
            e = str(e).strip()
            if e and "@" in e and e.lower() not in [x.lower() for x in cleaned]:
                cleaned.append(e)
        if not cleaned:
            cleaned = [self.gmail_user]
        os.makedirs(_DATA_DIR, exist_ok=True)
        import json
        with open(_RECIPIENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2)
        logger.info(f"[EmailService] Saved {len(cleaned)} alert recipient(s) to {_RECIPIENTS_FILE}")
        return cleaned

    def add_recipient(self, email: str) -> List[str]:
        """Adds a new recipient email address."""
        email = email.strip()
        if not email or "@" not in email:
            raise ValueError(f"Invalid email address: '{email}'")
        current = self.get_recipients()
        if email.lower() not in [x.lower() for x in current]:
            current.append(email)
            self.set_recipients(current)
        return current

    def remove_recipient(self, email: str) -> List[str]:
        """Removes a recipient email address."""
        email = email.strip().lower()
        current = self.get_recipients()
        current = [e for e in current if e.lower() != email]
        if not current:
            current = [self.gmail_user]
        self.set_recipients(current)
        return current

    def is_configured(self) -> bool:
        """Checks if Gmail SMTP credentials are ready to send."""
        app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip() or self.app_password
        user = os.getenv("GMAIL_USER", "").strip() or self.gmail_user
        return bool(user and app_pwd)

    def send_email(
        self,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
        image_attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Sends an email via Gmail SMTP.

        image_attachments format:
        [
            {"filename": "snap.jpg", "bytes": b'...', "content_id": "optional_cid"}
        ]
        """
        user = os.getenv("GMAIL_USER", "").strip() or self.gmail_user
        app_pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip() or self.app_password
        recipients = self._get_recipients(to_emails)

        if not user or not app_pwd:
            logger.warning(
                "[EmailService] Cannot send email: GMAIL_APP_PASSWORD is not configured in .env. "
                f"Alert '{subject}' was not dispatched to {recipients}."
            )
            return {
                "success": False,
                "error": "GMAIL_APP_PASSWORD is not configured in .env. Please set a 16-character Google App Password.",
            }

        if not recipients:
            logger.warning(f"[EmailService] No recipient emails found for '{subject}'.")
            return {"success": False, "error": "No recipient emails defined."}

        try:
            msg = MIMEMultipart("related")
            msg["From"] = f"विपद्Sathi Emergency Alert <{user}>"
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject

            alt_part = MIMEMultipart("alternative")
            if text_content:
                alt_part.attach(MIMEText(text_content, "plain", "utf-8"))
            alt_part.attach(MIMEText(html_content, "html", "utf-8"))
            msg.attach(alt_part)

            # Attach images
            if image_attachments:
                for img in image_attachments:
                    data = img.get("bytes")
                    fname = img.get("filename", "evidence.jpg")
                    cid = img.get("content_id")
                    if data:
                        part = MIMEImage(data, name=fname)
                        if cid:
                            part.add_header("Content-ID", f"<{cid}>")
                        part.add_header("Content-Disposition", f'inline; filename="{fname}"')
                        msg.attach(part)

            # Send via SMTP
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, app_pwd)
            server.sendmail(user, recipients, msg.as_string())
            server.quit()

            logger.info(f"[EmailService] Alert email '{subject}' delivered to {recipients}")
            return {"success": True, "recipients": recipients}

        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                f"[EmailService] Gmail SMTP Authentication Error: {e}. "
                "Ensure GMAIL_APP_PASSWORD is a 16-character App Password generated from Google Account Security."
            )
            return {"success": False, "error": f"SMTP Authentication failed: {e}"}
        except Exception as exc:
            logger.error(f"[EmailService] Failed to send email '{subject}': {exc}")
            return {"success": False, "error": str(exc)}

    # -------------------------------------------------------------------------
    # High-level Alert: Citizen Incident Report
    # -------------------------------------------------------------------------
    def send_citizen_report_email(
        self,
        report_id: str,
        incident_type: str,
        incident_time: str,
        location: str,
        description: str,
        saved_files: List[str],
        report_dir: str,
        to_emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Formats and sends an incident alert email for a citizen report."""
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        subject = f"🚨 [विपद्Sathi] CITIZEN REPORT: {incident_type} at {location} ({report_id})"

        # Clean description
        desc_clean = (description or "No additional description provided.").strip()

        # Check for image attachments
        image_attachments = []
        image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        attached_img_cids = []

        for idx, fname in enumerate(saved_files):
            _, ext = os.path.splitext(fname.lower())
            if ext in image_exts:
                full_path = os.path.join(report_dir, fname)
                if os.path.isfile(full_path):
                    try:
                        with open(full_path, "rb") as f:
                            img_data = f.read()
                        cid = f"img_evidence_{idx}"
                        image_attachments.append({
                            "filename": fname,
                            "bytes": img_data,
                            "content_id": cid,
                        })
                        attached_img_cids.append((fname, cid))
                    except Exception as e:
                        logger.warning(f"Failed to read image {full_path}: {e}")

        # Build inline image preview HTML if available
        evidence_html = ""
        if attached_img_cids:
            img_tags = "".join(
                f'<div style="margin-top:10px;"><img src="cid:{cid}" alt="{fname}" style="max-width:100%; border-radius:8px; border:1px solid #e0e0e0; box-shadow:0 2px 8px rgba(0,0,0,0.08);"><br><span style="font-size:12px; color:#666;">{fname}</span></div>'
                for fname, cid in attached_img_cids
            )
            evidence_html = f"""
            <div style="margin-top: 20px;">
                <strong style="color: #1a1a1a; font-size: 14px;">📸 Photo Evidence ({len(attached_img_cids)} attached):</strong>
                {img_tags}
            </div>
            """
        elif saved_files:
            evidence_html = f"""
            <div style="margin-top: 15px; font-size: 13px; color: #555;">
                <strong>Attached Files:</strong> {", ".join(saved_files)}
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6f8fa; margin: 0; padding: 24px; color: #24292e; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e1e4e8; box-shadow: 0 4px 16px rgba(0,0,0,0.05); }}
            .header {{ background: #b91c1c; color: #ffffff; padding: 24px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}
            .header p {{ margin: 6px 0 0; font-size: 13px; opacity: 0.9; }}
            .content {{ padding: 24px; }}
            .card {{ background: #fafbfc; border: 1px solid #e1e4e8; border-radius: 8px; padding: 18px; margin-bottom: 20px; }}
            .row {{ display: flex; margin-bottom: 10px; font-size: 14px; border-bottom: 1px dashed #eaecef; padding-bottom: 8px; }}
            .label {{ font-weight: 600; width: 140px; color: #586069; }}
            .value {{ font-weight: 500; color: #1a1a1a; flex: 1; }}
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 12px; background: #fee2e2; color: #991b1b; }}
            .desc-box {{ background: #f1f5f9; border-left: 4px solid #b91c1c; padding: 12px 16px; border-radius: 4px; font-size: 14px; line-height: 1.5; color: #334155; margin-top: 14px; }}
            .footer {{ background: #f6f8fa; padding: 16px; text-align: center; font-size: 12px; color: #6a737d; border-top: 1px solid #eaecef; }}
            .btn {{ display: inline-block; background: #b91c1c; color: #ffffff !important; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; margin-top: 15px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>विपद्Sathi CITIZEN INCIDENT REPORT</h1>
              <p>Immediate Authority Attention Required</p>
            </div>
            <div class="content">
              <div class="card">
                <div class="row">
                  <span class="label">Report ID:</span>
                  <span class="value"><code>{report_id}</code></span>
                </div>
                <div class="row">
                  <span class="label">Incident Type:</span>
                  <span class="value"><span class="badge">{incident_type}</span></span>
                </div>
                <div class="row">
                  <span class="label">Location:</span>
                  <span class="value"><strong>{location}</strong></span>
                </div>
                <div class="row">
                  <span class="label">Incident Time:</span>
                  <span class="value">{incident_time}</span>
                </div>
                <div class="row">
                  <span class="label">Received At:</span>
                  <span class="value">{now_str}</span>
                </div>
                <div class="row" style="border-bottom:none; margin-bottom:0; padding-bottom:0;">
                  <span class="label">Evidence:</span>
                  <span class="value">{len(saved_files)} file(s) attached</span>
                </div>
              </div>

              <div>
                <strong style="font-size:14px; color:#1a1a1a;">📝 Citizen Description:</strong>
                <div class="desc-box">{desc_clean}</div>
              </div>

              {evidence_html}

              <div style="text-align: center; margin-top: 24px;">
                <a href="http://localhost:3000/response-dashboard.html" class="btn">Open Operations Dashboard →</a>
              </div>
            </div>
            <div class="footer">
              विपद्Sathi Disaster & Incident Early Warning System &bull; Bagmati Operational Command<br>
              Automated alert sent from bipadsathi1@gmail.com
            </div>
          </div>
        </body>
        </html>
        """

        plain_text = (
            f"विपद्Sathi CITIZEN INCIDENT REPORT\n"
            f"----------------------------------------\n"
            f"Report ID: {report_id}\n"
            f"Incident: {incident_type}\n"
            f"Location: {location}\n"
            f"Incident Time: {incident_time}\n"
            f"Submitted: {now_str}\n"
            f"Files Attached: {len(saved_files)}\n\n"
            f"Description:\n{desc_clean}\n\n"
            f"Dashboard: http://localhost:3000/response-dashboard.html\n"
        )

        return self.send_email(
            subject=subject,
            html_content=html,
            text_content=plain_text,
            to_emails=to_emails,
            image_attachments=image_attachments,
        )

    # -------------------------------------------------------------------------
    # High-level Alert: Camera AI Detection
    # -------------------------------------------------------------------------
    def send_detection_email(
        self,
        cam_id: int,
        class_name: str,
        confidence: float,
        image_bytes: Optional[bytes] = None,
        vehicle_info: Optional[Dict[str, Any]] = None,
        to_emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Formats and sends an AI camera disaster detection alert email."""
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        label = class_name.replace("_", " ").upper()
        conf_pct = round(confidence * 100, 1) if confidence <= 1.0 else round(confidence, 1)

        subject = f"⚠️ [विपद्Sathi AI ALERT] {label} Detected on CAM-0{cam_id} ({conf_pct}%)"

        image_attachments = []
        img_html = ""
        if image_bytes:
            cid = "cam_snapshot"
            fname = f"detection_cam{cam_id}.jpg"
            image_attachments.append({
                "filename": fname,
                "bytes": image_bytes,
                "content_id": cid,
            })
            img_html = f"""
            <div style="margin-top: 20px;">
              <strong style="color: #1a1a1a; font-size: 14px;">📸 Camera Snapshot:</strong>
              <div style="margin-top: 8px;">
                <img src="cid:{cid}" alt="{fname}" style="max-width: 100%; border-radius: 8px; border: 1px solid #e1e4e8; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
              </div>
            </div>
            """

        accident_details = ""
        if vehicle_info and vehicle_info.get("vehicles_line"):
            accident_details = f"""
            <div class="row">
              <span class="label">Vehicles Involved:</span>
              <span class="value"><strong>{vehicle_info.get('vehicles_line', 'N/A')}</strong></span>
            </div>
            <div class="row">
              <span class="label">Ambulances Needed:</span>
              <span class="value"><span style="color:#b91c1c; font-weight:700;">{vehicle_info.get('ambulances_line', 'N/A')}</span></span>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f6f8fa; margin: 0; padding: 24px; color: #24292e; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e1e4e8; box-shadow: 0 4px 16px rgba(0,0,0,0.05); }}
            .header {{ background: #dc2626; color: #ffffff; padding: 24px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
            .header p {{ margin: 6px 0 0; font-size: 13px; opacity: 0.9; }}
            .content {{ padding: 24px; }}
            .card {{ background: #fafbfc; border: 1px solid #e1e4e8; border-radius: 8px; padding: 18px; margin-bottom: 20px; }}
            .row {{ display: flex; margin-bottom: 10px; font-size: 14px; border-bottom: 1px dashed #eaecef; padding-bottom: 8px; }}
            .label {{ font-weight: 600; width: 140px; color: #586069; }}
            .value {{ font-weight: 500; color: #1a1a1a; flex: 1; }}
            .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 12px; background: #fee2e2; color: #991b1b; }}
            .footer {{ background: #f6f8fa; padding: 16px; text-align: center; font-size: 12px; color: #6a737d; border-top: 1px solid #eaecef; }}
            .btn {{ display: inline-block; background: #dc2626; color: #ffffff !important; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; margin-top: 15px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>⚠️ विपद्Sathi AI DISASTER ALERT</h1>
              <p>Automated Visual Detection Confirmed</p>
            </div>
            <div class="content">
              <div class="card">
                <div class="row">
                  <span class="label">Camera ID:</span>
                  <span class="value"><strong>CAM-0{cam_id}</strong> (Bagmati Monitoring Grid)</span>
                </div>
                <div class="row">
                  <span class="label">Disaster Event:</span>
                  <span class="value"><span class="badge">{label}</span></span>
                </div>
                <div class="row">
                  <span class="label">Confidence:</span>
                  <span class="value"><strong>{conf_pct}%</strong></span>
                </div>
                <div class="row">
                  <span class="label">Detection Time:</span>
                  <span class="value">{now_str}</span>
                </div>
                <div class="row" style="border-bottom:none;">
                  <span class="label">Location:</span>
                  <span class="value">Bagmati Monitoring Zone</span>
                </div>
                {accident_details}
              </div>

              {img_html}

              <div style="text-align: center; margin-top: 24px;">
                <a href="http://localhost:3000/live-cameras.html" class="btn">View Live Camera Feed →</a>
              </div>
            </div>
            <div class="footer">
              विपद्Sathi Disaster Early Warning System &bull; Bagmati Operational Command<br>
              Automated alert sent from bipadsathi1@gmail.com
            </div>
          </div>
        </body>
        </html>
        """

        plain_text = (
            f"विपद्Sathi AI DISASTER ALERT\n"
            f"----------------------------------------\n"
            f"Camera: CAM-0{cam_id}\n"
            f"Event: {label}\n"
            f"Confidence: {conf_pct}%\n"
            f"Time: {now_str}\n"
            f"Location: Bagmati Monitoring Zone\n"
        )
        if vehicle_info and vehicle_info.get("vehicles_line"):
            plain_text += (
                f"Vehicles: {vehicle_info.get('vehicles_line')}\n"
                f"Ambulances: {vehicle_info.get('ambulances_line')}\n"
            )
        plain_text += "Live Feed: http://localhost:3000/live-cameras.html\n"

        return self.send_email(
            subject=subject,
            html_content=html,
            text_content=plain_text,
            to_emails=to_emails,
            image_attachments=image_attachments,
        )


email_service = EmailService()
