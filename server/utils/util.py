# utils/util.py
import random
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def send_otp_email(user_email, reason="signup"):
    # Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Subject + intro text depending on reason
    if reason == "signup":
        subject = "I2EDC — Complete Your Signup with OTP"
        intro = "Welcome to I2EDC! Use this OTP to complete your signup."
    elif reason == "forgotpassword":
        subject = "I2EDC — Reset Your Password (OTP)"
        intro = "We received a request to reset your password."
    else:
        subject = f"I2EDC — OTP for {reason}"
        intro = f"Use this OTP for {reason}."

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@i2edc.org")

    # Plain text (fallback)
    text_content = (
        f"{intro}\n\n"
        f"OTP: {otp}\n\n"
        f"This code will expire in 15 minutes.\n\n"
        f"If you didn’t request this, ignore this email."
    )

    # HTML content
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color:#333;">
      <h2 style="color:#0b5ed7;">I2EDC</h2>
      <p>{intro}</p>
      <div style="margin:20px 0; padding:12px; background:#f7f9ff; text-align:center; border-radius:6px;">
        <span style="font-size:28px; font-weight:bold; letter-spacing:3px;">{otp}</span>
      </div>
      <p>This code will expire in <strong>15 minutes</strong>.</p>
      <hr style="border:none; border-top:1px solid #eee; margin:20px 0;" />
      <p style="font-size:12px; color:#888;">Do not reply to this email. If you didn’t request this, you can safely ignore it.</p>
    </body>
    </html>
    """

    msg = EmailMultiAlternatives(subject, text_content, from_email, [user_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    return otp


def send_notification_email(recipient_email, template_type, context=None):
    """
    Send a generic notification email based on a template type.
    
    Args:
        recipient_email (str): The email address of the recipient.
        template_type (str): The type of email template ('service_request_admin', 'service_request_status', 'contact_form', 'event_registration').
        context (dict): Dynamic data to populate the template.
    """
    if context is None:
        context = {}

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@i2edc.org")
    subject = "I2EDC Notification"
    intro = "You have a new notification."
    details_html = ""

    # --- 1. ADMIN: New Service Request ---
    if template_type == "service_request_admin":
        service_name = context.get("service_name", "Unknown Service")
        user_name = context.get("user_name", "Unknown User")
        plan_name = context.get("plan_name", "Unknown Plan")
        
        subject = f"New Service Request: {service_name}"
        intro = f"User <strong>{user_name}</strong> has requested the service <strong>{service_name}</strong>."
        details_html = f"""
        <div style="background:#f7f9ff; padding:15px; border-radius:6px; margin:20px 0;">
            <p style="margin:5px 0;"><strong>Plan:</strong> {plan_name}</p>
            <p style="margin:5px 0;"><strong>Requested At:</strong> {context.get('requested_at', 'Just now')}</p>
        </div>
        <p>Please log in to the admin panel to review and approve this request.</p>
        """

    # --- 2. USER: Service Request Confirmation ---
    elif template_type == "service_request_user_confirmation":
        service_name = context.get("service_name", "Service")
        user_name = context.get("user_name", "User")
        
        subject = f"Request Received: {service_name}"
        intro = f"Hi {user_name}, we have received your request for <strong>{service_name}</strong>."
        details_html = f"""
        <p>Our team will review your request and get back to you shortly.</p>
        <p>You can track the status of your request in your dashboard.</p>
        """

    # --- 3. USER: Service Request Status Update ---
    elif template_type == "service_request_status":
        service_name = context.get("service_name", "Unknown Service")
        status = context.get("status", "UPDATED")
        
        subject = f"Update on your request for {service_name}"
        intro = f"The status of your request for <strong>{service_name}</strong> has been updated."
        
        status_color = "#333"
        if status == "APPROVED": status_color = "#198754" # Green
        elif status == "REJECTED": status_color = "#dc3545" # Red
        elif status == "COMPLETED": status_color = "#0d6efd" # Blue
        
        details_html = f"""
        <div style="text-align:center; margin:30px 0;">
            <span style="font-size:20px; font-weight:bold; color:{status_color}; border:2px solid {status_color}; padding: 10px 20px; border-radius:50px;">
                {status}
            </span>
        </div>
        <p>Check your dashboard for more details or remarks from the admin.</p>
        """

    # --- 3. ADMIN: Contact Form Submission ---
    elif template_type == "contact_form":
        name = context.get("name", "Visitor")
        email = context.get("email", "No email")
        msg_subject = context.get("subject", "No subject")
        message = context.get("message", "")
        
        subject = f"New Inquiry: {msg_subject}"
        intro = f"You have received a new message from <strong>{name}</strong> ({email})."
        details_html = f"""
        <div style="background:#fff3cd; padding:15px; border-radius:6px; margin:20px 0; border-left: 4px solid #ffc107;">
            <p style="margin:0; font-style:italic;">"{message}"</p>
        </div>
        """

    # --- 4. ADMIN: Event Registration Notification ---
    elif template_type == "event_registration_admin":
        event_name = context.get("event_name", "Event")
        user_name = context.get("user_name", "User")
        user_email = context.get("user_email", "No email")
        
        subject = f"New Registration for {event_name}"
        intro = f"User <strong>{user_name}</strong> ({user_email}) has registered for your event <strong>{event_name}</strong>."
        details_html = f"""
        <div style="background:#f7f9ff; padding:15px; border-radius:6px; margin:20px 0;">
            <p style="margin:5px 0;"><strong>Event:</strong> {event_name}</p>
            <p style="margin:5px 0;"><strong>Participant:</strong> {user_name} ({user_email})</p>
        </div>
        """

    # --- 5. USER: Event Registration ---
    elif template_type == "event_registration":
        event_name = context.get("event_name", "Event")
        event_date = context.get("event_date", "Upcoming")
        
        subject = f"Registration Confirmed: {event_name}"
        intro = f"You have successfully registered for <strong>{event_name}</strong>!"
        details_html = f"""
        <div style="background:#d1e7dd; padding:15px; border-radius:6px; margin:20px 0;">
            <p style="margin:5px 0;"><strong>Date:</strong> {event_date}</p>
            <p style="margin:5px 0;"><strong>Location:</strong> Online / See details</p>
        </div>
        <p>We look forward to seeing you there!</p>
        """

    # --- 6a. REMARK: To Sender (Confirmation) ---
    elif template_type == "service_remark_sender":
        service_name = context.get("service_name", "Service")
        message_snippet = context.get("message", "")
        
        subject = f"Message Sent: {service_name}"
        intro = f"You sent a new message regarding <strong>{service_name}</strong>."
        details_html = f"""
        <div style="background:#eef2f5; padding:15px; border-radius:6px; margin:20px 0; border-left: 4px solid #6c757d;">
            <p style="margin:0; font-style:italic;">"{message_snippet}"</p>
        </div>
        """

    # --- 6b. REMARK: To Recipient (Notification) ---
    elif template_type == "service_remark_recipient":
        service_name = context.get("service_name", "Service")
        sender_name = context.get("sender_name", "User")
        message_snippet = context.get("message", "")
        
        subject = f"New Message: {service_name}"
        intro = f"<strong>{sender_name}</strong> sent you a message regarding <strong>{service_name}</strong>."
        details_html = f"""
        <div style="background:#eef2f5; padding:15px; border-radius:6px; margin:20px 0; border-left: 4px solid #6c757d;">
            <p style="margin:0; font-style:italic;">"{message_snippet}"</p>
        </div>
        <p>Please log in to your dashboard to view the full conversation and reply.</p>
        """

    # Construct HTML Body
    html_content = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#333; line-height:1.6;">
      <div style="max-width:600px; margin:0 auto; padding:20px; border:1px solid #eee; border-radius:10px;">
          <h2 style="color:#0b5ed7; border-bottom:2px solid #0b5ed7; padding-bottom:10px;">I2EDC</h2>
          
          <p style="font-size:16px;">{intro}</p>
          
          {details_html}
          
          <hr style="border:none; border-top:1px solid #eee; margin:30px 0;" />
          
          <p style="font-size:12px; color:#888; text-align:center;">
            &copy; {getattr(settings, 'COPYRIGHT_YEAR', '2025')} I2EDC. All rights reserved.<br>
            This is an automated message, please do not reply.
          </p>
      </div>
    </body>
    </html>
    """
    
    # Text Body (Fallback)
    text_content = f"{intro}\n\n[Displaying HTML Content is required to view details]\n\nI2EDC Team"

    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print(f"[EMAIL SENT] Type: {template_type} | To: {recipient_email} | Subject: {subject}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

