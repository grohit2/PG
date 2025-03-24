import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

def send_email_via_gmail(recipient_email, subject, body, attachments=None):
    # Your Gmail credentials
    sender_email = "300kbiz6m@gmail.com"  # Replace with your Gmail address
    app_password = "ripf gkno rxii xhpu"  # Replace with your App Password
    
    # Create message container
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    # Attach body text
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach files if any
    if attachments:
        for file_path in attachments:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file:
                    file_attachment = MIMEApplication(file.read())
                file_name = os.path.basename(file_path)
                file_attachment.add_header('Content-Disposition', 'attachment', filename=file_name)
                msg.attach(file_attachment)
    
    try:
        # Create secure connection with Gmail's SMTP server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print(f"Email successfully sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
        return False

# Example usage
if __name__ == "__main__":
    recipient = "recipient@example.com"  # Replace with recipient's email
    email_subject = "Test Email from Python"
    email_body = "Hello!\n\nThis is a test email sent from my Python program running on my local desktop.\n\nRegards,\nYour Name"
    
    # Optional: Add file attachments (comment out if not needed)
    # files_to_attach = ["path/to/document.pdf", "path/to/image.jpg"]
    
    # Send without attachments
    send_email_via_gmail(recipient, email_subject, email_body)
    
    # Send with attachments (uncomment if needed)
    # send_email_via_gmail(recipient, email_subject, email_body, files_to_attach)