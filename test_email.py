import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email configuration
MAIL_SERVER = os.environ.get('MAIL_SERVER')
MAIL_PORT = int(os.environ.get('MAIL_PORT'))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
RECIPIENT = os.environ.get('REPORT_RECIPIENTS')

print(f"Mail settings:")
print(f"Server: {MAIL_SERVER}")
print(f"Port: {MAIL_PORT}")
print(f"TLS: {MAIL_USE_TLS}")
print(f"Username: {MAIL_USERNAME}")
print(f"Password: {'*' * len(MAIL_PASSWORD) if MAIL_PASSWORD else 'Not set'}")
print(f"Sender: {MAIL_DEFAULT_SENDER}")
print(f"Recipient: {RECIPIENT}")

try:
    # Create message
    msg = MIMEMultipart()
    msg['From'] = MAIL_DEFAULT_SENDER
    msg['To'] = RECIPIENT
    msg['Subject'] = 'Test Email from Attendance System'
    
    body = 'This is a test email from the Attendance System.'
    msg.attach(MIMEText(body, 'plain'))
    
    # Connect to server
    print("\nConnecting to mail server...")
    if MAIL_USE_TLS:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT)
    
    # Login
    print("Logging in...")
    server.login(MAIL_USERNAME, MAIL_PASSWORD)
    
    # Send email
    print("Sending email...")
    text = msg.as_string()
    server.sendmail(MAIL_DEFAULT_SENDER, RECIPIENT, text)
    
    # Close connection
    print("Closing connection...")
    server.quit()
    
    print("Email sent successfully!")
except Exception as e:
    print(f"Error sending email: {str(e)}")
