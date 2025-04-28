import imaplib

# Import from your processor to ensure credentials are correct
from gmail_processor import GMAIL_USER, GMAIL_PASSWORD, GMAIL_SERVER

def test_gmail_connection():
    """Test connection to Gmail."""
    try:
        print(f"Connecting to {GMAIL_SERVER}...")
        mail = imaplib.IMAP4_SSL(GMAIL_SERVER)
        
        print(f"Logging in as {GMAIL_USER}...")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        
        print("Login successful!")
        
        # Check available mailboxes
        print("\nAvailable mailboxes:")
        status, mailboxes = mail.list()
        for i, mailbox in enumerate(mailboxes[:5]):  # Show first 5 mailboxes
            print(f"  {mailbox.decode()}")
        if len(mailboxes) > 5:
            print(f"  ...and {len(mailboxes) - 5} more")
        
        # Check INBOX
        print("\nChecking INBOX...")
        mail.select("INBOX")
        
        # Get message count
        status, data = mail.search(None, "ALL")
        message_count = len(data[0].split())
        print(f"Found {message_count} total messages in INBOX")
        
        # Check for unread messages
        status, data = mail.search(None, "UNSEEN")
        unread_count = len(data[0].split())
        print(f"Found {unread_count} unread messages in INBOX")
        
        # Logout
        mail.logout()
        print("\nLogout successful")
        print("Connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error testing Gmail connection: {str(e)}")
        return False

if __name__ == "__main__":
    test_gmail_connection()