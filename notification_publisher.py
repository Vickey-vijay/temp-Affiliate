# notification_publisher.py

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationPublisher:
    """
    Handles notifications for publishing products by sending messages via Telegram, WhatsApp,
    and sending email reports.
    """
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.telegram_config = self.config_manager.get_telegram_config()
        self.whatsapp_config = self.config_manager.get_whatsapp_config()
        # Initialize email_config properly
        self.email_config = self.config_manager.get_email_config()



    def telegram_push(self, product: dict):
        """
        Sends a notification to Telegram with product details.
        :param product: Dictionary containing product information.
        """
        bot_token = self.telegram_config.get("bot_token")
        group_ids = self.telegram_config.get("group_ids", "")
        if not bot_token or not group_ids:
            print("[Telegram] Bot token or group IDs not configured.")
            return

        message = self.format_product_message(product)
        for group_id in group_ids.split(","):
            group_id = group_id.strip()
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": group_id,
                "text": message,
                "parse_mode": "HTML"
            }
            try:
                response = requests.post(url, data=payload)
                if response.status_code != 200:
                    print(f"[Telegram] Failed to send message to {group_id}: {response.text}")
            except Exception as e:
                print(f"[Telegram] Exception occurred: {e}")

    def whatsapp_push(self, product: dict):
        """
        Automates sending a message to WhatsApp using stored cookies.
        This is a placeholder. In production, you may use Selenium or another automation tool.
        :param product: Dictionary containing product information.
        """
        message = self.format_product_message(product)
        print(f"[WhatsApp] (Placeholder) Sending message: {message}")
        # Use self.whatsapp_config.get("cookies") and automation logic here.

    def format_product_message(self, product: dict) -> str:
        """
        Formats the product details into a message string.
        :param product: Dictionary containing product information.
        :return: Formatted message string.
        """
        title = product.get("product_name", "Unnamed Product")
        current_price = product.get("Product_current_price", "N/A")
        mrp = product.get("Product_lowest_price", "N/A")
        buy_now_url = product.get("product_Affiliate_url", "#")
        image_url = product.get("Product_image_path", "")
        message = (
            f"<b>{title}</b>\n"
            f"Current Price: {current_price}\n"
            f"MRP: {mrp}\n"
            f"<a href='{buy_now_url}'>Buy Now</a>\n"
            f"{'Image: ' + image_url if image_url else ''}"
        )
        return message

    def send_email_report(self, recipients: list, subject: str, report_file: str, body: str = ""):
        """
        Sends an email with the report attached.
        :param recipients: List of recipient email addresses.
        :param subject: Subject of the email.
        :param report_file: Path to the report file (CSV or Excel) to attach.
        :param body: Email body text.
        """
        smtp_server = self.email_config.get("smtp_server", "smtp.example.com")
        smtp_port = int(self.email_config.get("smtp_port", 587))
        smtp_username = self.email_config.get("smtp_username", "your_email@example.com")
        smtp_password = self.email_config.get("smtp_password", "your_email_password")
        from_email = smtp_username

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with open(report_file, "rb") as f:
                attachment = MIMEText(f.read(), "base64", "utf-8")
                attachment.add_header("Content-Disposition", "attachment", filename=report_file)
                msg.attach(attachment)
        except Exception as e:
            print(f"[Email] Failed to attach report file: {e}")
            return

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(from_email, recipients, msg.as_string())
            server.quit()
            print(f"[Email] Report sent successfully to {recipients}")
        except Exception as e:
            print(f"[Email] Failed to send email: {e}")
