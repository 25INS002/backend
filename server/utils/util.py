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
