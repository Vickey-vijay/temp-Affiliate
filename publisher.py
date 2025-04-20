# publisher.py

import os
import json
import requests
import datetime
from pymongo import MongoClient
import pandas as pd
from utils.email_sender import EmailSender  # You can implement this in another file
from utils.whatsapp_sender import WhatsappSender  # You can implement this in another file

class Publisher:
    def __init__(self, mongo_uri="mongodb://localhost:27017/", db_name="your_database_name"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.products_collection = self.db["products"]
        self.published_collection = self.db["published_products"]
        self.config = self.load_config()
        self.whatsapp = WhatsappSender()
        self.email_sender = EmailSender()

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print("Failed to load config:", e)
            return {}

    def telegram_push(self, product_data):
        try:
            bot_token = self.config["telegram"]["bot_token"]
            chat_id = self.config["telegram"]["chat_id"]

            message = (
                f"🔥 *{product_data['product_name']}*\n"
                f"💰 *Current Price:* ₹{product_data['price']}\n"
                f"💸 *MRP:* ₹{product_data.get('mrp', 'N/A')}\n"
                f"🛒 [Buy Now]({product_data['product_url']})"
            )

            image_url = product_data.get("image_url")
            telegram_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

            response = requests.post(telegram_url, data={
                "chat_id": chat_id,
                "caption": message,
                "parse_mode": "Markdown"
            }, files={
                "photo": requests.get(image_url, stream=True).raw if image_url else None
            })

            if response.status_code == 200:
                print("✅ Telegram message sent.")
            else:
                print("❌ Telegram failed:", response.text)

        except Exception as e:
            print("❌ Telegram push error:", e)

    def whatsapp_push(self, product_data):
        try:
            self.whatsapp.send_message(product_data)
            print("✅ WhatsApp message sent.")
        except Exception as e:
            print("❌ WhatsApp push error:", e)

    def generate_report(self, period="daily"):
        """
        period can be 'daily', 'weekly', 'monthly'
        """
        now = datetime.datetime.now()
        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start = now - datetime.timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError("Invalid period")

        end = now
        query = {"published_at": {"$gte": start, "$lte": end}}
        published_products = list(self.published_collection.find(query))

        if not published_products:
            print(f"📭 No {period} products found.")
            return None

        df = pd.DataFrame(published_products)
        filename = f"{period}_report_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        return filename

    def send_scheduled_report(self):
        try:
            for period in ["daily", "weekly", "monthly"]:
                file_path = self.generate_report(period)
                if file_path:
                    self.email_sender.send_email(
                        subject=f"{period.capitalize()} Product Report",
                        body="Please find the attached report.",
                        attachments=[file_path]
                    )
                    os.remove(file_path)
        except Exception as e:
            print("❌ Report email sending failed:", e)
