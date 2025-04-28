import time
import sys
from gmail_processor import check_gmail_for_updates

def main():
    """Run the Gmail checker on a schedule."""
    interval_minutes = 5  # Check every 5 minutes
    
    print(f"Starting Gmail checker. Will check every {interval_minutes} minutes.")
    print(f"Checking for emails sent to: {GMAIL_USER}")
    print("Press Ctrl+C to exit.")
    
    try:
        while True:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking for new emails...")
            check_gmail_for_updates()
            
            # Wait for the next check
            print(f"Next check in {interval_minutes} minutes...")
            for i in range(interval_minutes * 60):
                time.sleep(1)
                # Add a simple progress indicator every minute
                if i % 60 == 0 and i > 0:
                    minutes_passed = i // 60
                    minutes_left = interval_minutes - minutes_passed
                    print(f"  {minutes_left} minutes until next check...")
                    
    except KeyboardInterrupt:
        print("\nGmail checker stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error in main loop: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    from gmail_processor import GMAIL_USER
    main()