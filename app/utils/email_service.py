import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from flask import current_app
import logging

def send_email(subject, recipients, text_body, html_body=None, attachments=None):
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = current_app.config.get('MAIL_DEFAULT_SENDER')
        msg['To'] = ', '.join(recipients)

        # Attach text body
        msg.attach(MIMEText(text_body, 'plain'))

        # Attach HTML body if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))

        # Attach files if provided
        if attachments:
            for filename, content_type, data in attachments:
                attachment = MIMEApplication(data)
                attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(attachment)

        # Log email details
        current_app.logger.info(f"Sending email to: {', '.join(recipients)}")
        current_app.logger.info(f"Subject: {subject}")

        # Send email using SMTP with detailed logging
        try:
            current_app.logger.info(f"Connecting to mail server {current_app.config.get('MAIL_SERVER')}:{current_app.config.get('MAIL_PORT')}")
            server = smtplib.SMTP(current_app.config.get('MAIL_SERVER'), current_app.config.get('MAIL_PORT'))

            # Set debug level for more verbose output
            server.set_debuglevel(1)

            # Identify ourselves to the server
            server.ehlo()

            if current_app.config.get('MAIL_USE_TLS'):
                current_app.logger.info("Starting TLS encryption")
                server.starttls()
                # Re-identify ourselves over TLS connection
                server.ehlo()

            # Login if username and password are provided
            if current_app.config.get('MAIL_USERNAME') and current_app.config.get('MAIL_PASSWORD'):
                username = current_app.config.get('MAIL_USERNAME')
                password = current_app.config.get('MAIL_PASSWORD')
                current_app.logger.info(f"Logging in with username: {username}")
                current_app.logger.info(f"Password length: {len(password)}")
                server.login(username, password)

            # Send email
            current_app.logger.info(f"Sending email from: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
            server.sendmail(
                current_app.config.get('MAIL_DEFAULT_SENDER'),
                recipients,
                msg.as_string()
            )

            # Close the connection
            server.quit()
        except Exception as e:
            current_app.logger.error(f"SMTP Error: {str(e)}")
            raise

        current_app.logger.info(f"Email sent successfully to: {', '.join(recipients)}")
        return True

    except Exception as e:
        current_app.logger.error(f"Error sending email: {str(e)}")
        return False

def send_report_email(subject, recipients, report_data, month_name, year, attachments=None):
    
    # Create HTML email body
    html_body = f'''
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; font-size: 24px; margin-bottom: 20px; }}
            p {{ margin-bottom: 15px; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Monthly Attendance Report - {month_name} {year}</h1>
            <p>Dear Staff,</p>
            <p>Please find attached the attendance report for {month_name} {year}.</p>
            <p>This report includes:</p>
            <ul>
                <li>Daily attendance summary</li>
                <li>Student-wise attendance details</li>
            </ul>
            <p>The report shows that out of {len(report_data['student_summary'])} students:</p>
            <ul>
                <li>{sum(1 for s in report_data['student_summary'] if s['attendance_percentage'] >= 90)} students have excellent attendance (90% or above)</li>
                <li>{sum(1 for s in report_data['student_summary'] if 75 <= s['attendance_percentage'] < 90)} students have good attendance (75-89%)</li>
                <li>{sum(1 for s in report_data['student_summary'] if s['attendance_percentage'] < 75)} students need attention (below 75%)</li>
            </ul>
            <p>Please review the attached files for detailed information.</p>
            <p>Thank you,</p>
            <p>Student Attendance System</p>
            <div class="footer">
                <p>This is an automated email. Please do not reply to this message.</p>
            </div>
        </div>
    </body>
    </html>
    '''

    # Create plain text version as fallback
    text_body = f'''
    Monthly Attendance Report - {month_name} {year}

    Dear Staff,

    Please find attached the attendance report for {month_name} {year}.

    This report includes:
    - Daily attendance summary
    - Student-wise attendance details

    The report shows that out of {len(report_data['student_summary'])} students:
    - {sum(1 for s in report_data['student_summary'] if s['attendance_percentage'] >= 90)} students have excellent attendance (90% or above)
    - {sum(1 for s in report_data['student_summary'] if 75 <= s['attendance_percentage'] < 90)} students have good attendance (75-89%)
    - {sum(1 for s in report_data['student_summary'] if s['attendance_percentage'] < 75)} students need attention (below 75%)

    Please review the attached files for detailed information.

    Thank you,
    Student Attendance System

    This is an automated email. Please do not reply to this message.
    '''

    return send_email(subject, recipients, text_body, html_body, attachments)
