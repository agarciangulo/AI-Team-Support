import imaplib
import email
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import traceback
from datetime import datetime, timedelta

from core.task_extractor import extract_tasks_from_update
from core.task_processor import insert_or_update_task
from core import fetch_notion_tasks
from core.openai_client import get_coaching_insight

# Gmail settings - UPDATE THESE WITH YOUR INFO
GMAIL_USER = "task.manager.mpiv@gmail.com"  # Replace with your Gmail address
GMAIL_PASSWORD = "fjohbugkfbkpgahg"  # Replace with your App Password (no spaces)
GMAIL_SERVER = "imap.gmail.com"

def send_confirmation_email(recipient, tasks, coaching_insights=None):
    """
    Send a confirmation email with processed tasks and coaching insights.
    
    Args:
        recipient: Email address to send to
        tasks: List of processed tasks
        coaching_insights: Optional coaching insights text
    """
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = GMAIL_USER
        msg['To'] = recipient
        msg['Subject'] = f"Task Manager: {len(tasks)} Tasks Processed"
        
        # Create plain text email
        text_content = f"Hello,\n\nWe've processed your email and extracted {len(tasks)} tasks:\n\n"
        
        for i, task in enumerate(tasks, 1):
            status = task.get('status', 'Unknown')
            category = task.get('category', 'Uncategorized')
            text_content += f"{i}. {task['task']} ({status}) - {category}\n"
        
        # Add coaching insights if available
        if coaching_insights:
            text_content += "\n\n--- AI Coaching Insights ---\n\n"
            text_content += coaching_insights
            text_content += "\n\n" + "-"*40
            
        text_content += "\n\nThank you for using the Task Manager!\n"
        
        # Create HTML version
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #4361ee; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .task {{ margin-bottom: 10px; padding: 10px; background-color: #f8f9fa; border-left: 4px solid #4361ee; }}
                .status {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
                .status-completed {{ background-color: #10b981; color: white; }}
                .status-in-progress {{ background-color: #3b82f6; color: white; }}
                .status-pending {{ background-color: #f59e0b; color: white; }}
                .status-blocked {{ background-color: #ef4444; color: white; }}
                .insights {{ margin-top: 30px; padding: 15px; background-color: #edf2fb; border-left: 4px solid #4361ee; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Task Manager Update</h2>
            </div>
            <div class="content">
                <p>We've processed your email and extracted {len(tasks)} tasks:</p>
                
                <div class="tasks">
        """
        
        for i, task in enumerate(tasks, 1):
            status = task.get('status', 'Unknown')
            category = task.get('category', 'Uncategorized')
            status_class = f"status-{status.lower().replace(' ', '-')}"
            
            html_content += f"""
                <div class="task">
                    <strong>{i}. {task['task']}</strong><br>
                    <span class="status {status_class}">{status}</span>
                    <span style="margin-left: 10px; color: #666;">Category: {category}</span>
                </div>
            """
        
        # Add coaching insights if available
        if coaching_insights:
            html_content += f"""
                <div class="insights">
                    <h3>AI Coaching Insights</h3>
                    <p>{coaching_insights.replace('\n', '<br>')}</p>
                </div>
            """
        
        html_content += """
                </div>
                
                <p>Thank you for using the Task Manager!</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
            
        print(f"Confirmation email sent to {recipient}")
        return True
        
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
        print(traceback.format_exc())
        return False

def check_gmail_for_updates():
    """Check Gmail for new emails and process them."""
    try:
        # Connect to Gmail
        print(f"Connecting to {GMAIL_SERVER}...")
        mail = imaplib.IMAP4_SSL(GMAIL_SERVER)
        
        # Login
        print(f"Logging in as {GMAIL_USER}...")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        
        # Select inbox
        mail.select("INBOX")
        
        # Search for unread messages
        status, message_ids = mail.search(None, "UNSEEN")
        
        if status != "OK" or not message_ids[0]:
            print("No new emails found")
            mail.close()
            mail.logout()
            return
            
        message_id_list = message_ids[0].split()
        print(f"Found {len(message_id_list)} new email(s)")
            
        # Process each unread message
        for msg_id in message_id_list:
            print(f"Processing email ID: {msg_id.decode()}")
            
            # Fetch the email
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                print(f"Error fetching message {msg_id}: {status}")
                continue
                
            # Parse the email
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get email details
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
                
            # Get sender info
            from_header = msg["From"]
            sender_name = from_header.split('<')[0].strip() if '<' in from_header else from_header.split('@')[0]
            sender_email = from_header.split('<')[1].split('>')[0] if '<' in from_header else from_header
            
            # Get date
            date_str = datetime.now().strftime("%Y-%m-%d")
            if msg["Date"]:
                try:
                    from email.utils import parsedate_to_datetime
                    email_date = parsedate_to_datetime(msg["Date"])
                    date_str = email_date.strftime("%Y-%m-%d")
                except:
                    pass  # Use today's date as fallback
            
            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue
                    
                    # Get text content
                    if content_type == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or "utf-8"
                            body = payload.decode(charset)
                            break  # Use the first text/plain part
                        except:
                            pass
            else:
                # Not multipart - get payload directly
                content_type = msg.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = msg.get_payload(decode=True)
                        charset = msg.get_content_charset() or "utf-8"
                        body = payload.decode(charset)
                    except:
                        pass
            
            if not body:
                print("Could not extract email body")
                continue
                
            # Format the update text
            update_text = f"From: {sender_name}\nDate: {date_str}\n\nSubject: {subject}\n\n{body}"
            
            print(f"Processing email from {sender_name} with subject: {subject}")
            
            try:
                # Extract tasks
                tasks = extract_tasks_from_update(update_text)
                
                if tasks:
                    print(f"Extracted {len(tasks)} tasks")
                    
                    # Get existing tasks
                    existing_tasks = fetch_notion_tasks()
                    
                    # Process each task
                    log_output = []
                    for task in tasks:
                        insert_or_update_task(task, existing_tasks, log_output)
                    
                    print(f"Successfully processed {len(tasks)} tasks")
                    
                    # Generate coaching insights
                    coaching_insights = None
                    try:
                        # Get person name from the first task
                        person_name = ""
                        if tasks and "employee" in tasks[0]:
                            person_name = tasks[0].get("employee", "")
                            
                        if person_name:
                            # Get recent tasks for this person
                            recent_tasks = existing_tasks[existing_tasks['employee'] == person_name]
                            if len(recent_tasks) > 0:
                                # Filter to recent tasks (last 14 days)
                                recent_tasks = recent_tasks[recent_tasks['date'] >= datetime.now() - timedelta(days=14)]
                                
                            # Get peer feedback
                            peer_feedback = []
                            try:
                                from core import fetch_peer_feedback
                                peer_feedback = fetch_peer_feedback(person_name)
                            except Exception as e:
                                print(f"Error fetching peer feedback: {str(e)}")
                                
                            # Generate coaching insights
                            coaching_insights = get_coaching_insight(person_name, tasks, recent_tasks, peer_feedback)
                            print("Generated coaching insights successfully")
                    except Exception as e:
                        print(f"Error generating coaching insights: {str(e)}")
                        print(traceback.format_exc())
                        
                    # Send confirmation with coaching insights
                    send_confirmation_email(sender_email, tasks, coaching_insights)
                else:
                    print("No tasks could be extracted from email")
            except Exception as e:
                print(f"Error processing email: {str(e)}")
                print(traceback.format_exc())
                
            # Mark the email as read
            mail.store(msg_id, "+FLAGS", "\\Seen")
            
        # Close the connection
        mail.close()
        mail.logout()
        print("Email processing completed")
        
    except Exception as e:
        print(f"Error checking Gmail: {str(e)}")
        print(traceback.format_exc())
        
if __name__ == "__main__":
    # Run once when executed directly
    check_gmail_for_updates()