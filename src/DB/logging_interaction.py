import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
mongo_db_action = os.getenv("MONGO_DB_ACTION")
smtp_email = os.getenv("SMTP_EMAIL")        # your sender email
smtp_password = os.getenv("SMTP_PASSWORD")  # your email app password
smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
smtp_port = int(os.getenv("SMTP_PORT", 587))

# MongoDB setup
mongo_client = MongoClient(mongo_uri)
mongo_action_db = mongo_client[mongo_db_action]
actions_collection = mongo_action_db["actions"]
users_collection = mongo_action_db["users"]


def notify_incremental(threshold: int, email: str) -> None:
    """
    Checks if the number of entries in actions_collection exceeds the threshold.
    If yes, sends an SMTP email notification.
    """
    try:
        count = actions_collection.count_documents({})
        print(f"[INFO] Actions count: {count}, Threshold: {threshold}")

        if count >= threshold:
            # --- Prepare Email ---
            subject = "Incremental Training Notification"
            body = (
                f"The actions collection now contains {count} entries, "
                f"which exceeds the threshold of {threshold}.\n\n"
                f"Please run the incremental file to update the model."
            )

            msg = MIMEMultipart()
            msg["From"] = smtp_email
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # --- Send Email ---
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_email, smtp_password)
                server.send_message(msg)

            print(f"[INFO] Notification sent successfully to {email}")

        else:
            print(f"[INFO] Threshold not reached yet ({count}/{threshold})")

    except Exception as e:
        print(f"[ERROR] notify_incremental failed: {e}")

if __name__ == "__main__":
  notify_incremental(2, email="b22cs006@iitj.ac.in")
