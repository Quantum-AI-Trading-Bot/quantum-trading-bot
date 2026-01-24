#!/usr/bin/env python3
"""
Email Sender via SMTP - Direct SMTP delivery
Updated: 2026-01-22 09:56:00 UTC
Purpose: Send email reports via 1&1 SMTP (smtp.1und1.de)
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# SMTP Configuration (1&1)
SMTP_HOST = "smtp.1und1.de"
SMTP_PORT = 587
SMTP_USER = "david@sanker.at"
SMTP_PASSWORD = "cik211ii51und1"
SMTP_FROM = "david@sanker.at"
SMTP_USE_TLS = True

def send_email(subject, body, to_email, from_email=None):
    """
    Send email via SMTP

    Args:
        subject: Email subject
        body: Email body (plaintext)
        to_email: Recipient email
        from_email: Sender email (default: SMTP_FROM)

    Returns:
        True if successful, False otherwise
    """
    if from_email is None:
        from_email = SMTP_FROM

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

        # Attach body
        msg.attach(MIMEText(body, 'plain'))

        # Connect to SMTP server with verbose logging
        print(f"Connecting to {SMTP_HOST}:{SMTP_PORT}...")

        if SMTP_USE_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.set_debuglevel(1)  # Enable debug output
            server.ehlo()
            server.starttls()
            server.ehlo()
            print("STARTTLS established")
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.ehlo()

        print(f"Authenticating as {SMTP_USER}...")
        # Login
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("Authentication successful")

        # Send
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        print(f"Email sent to {to_email}")

        server.quit()

        return True, ""

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        return False, error_msg

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Send email via SMTP')
    parser.add_argument('--to', required=True, help='Recipient email')
    parser.add_argument('--subject', default='Test Email', help='Email subject')
    parser.add_argument('--body', default='This is a test email.', help='Email body')
    parser.add_argument('--file', help='Read body from file')
    parser.add_argument('--quiet', action='store_true', help='Suppress debug output')

    args = parser.parse_args()

    # Read body from file if specified
    if args.file:
        with open(args.file, 'r') as f:
            body = f.read()
    else:
        body = args.body

    # Disable debug if quiet mode
    if args.quiet:
        import smtplib
        # Monkey-patch to disable debug
        original_init = smtplib.SMTP.__init__
        def quiet_init(self, host='', port=0, local_hostname=None, timeout=None):
            original_init(self, host, port, local_hostname, timeout)
            self.debuglevel = 0
        smtplib.SMTP.__init__ = quiet_init

    # Send email
    success, error = send_email(args.subject, body, args.to)

    if success:
        print(f"✓ Email sent successfully to {args.to}")
        sys.exit(0)
    else:
        print(f"✗ Failed to send email: {error}", file=sys.stderr)
        sys.exit(1)
