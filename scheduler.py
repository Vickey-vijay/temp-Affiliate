import schedule
import threading
import time
from datetime import datetime
from utils.email_sender import EmailSender


class Scheduler:
    def __init__(self, products_collection, published_collection, publisher, hands_off_controller, config_manager):
        self.products_collection = products_collection
        self.published_collection = published_collection
        self.publisher = publisher
        self.hands_off_controller = hands_off_controller
        self.config_manager = config_manager
        self.email_sender = EmailSender(config_manager)

    def start(self):
        """
        Start the scheduling in a background thread.
        """
        schedule.every(6).hours.do(self.hands_off_job)
        schedule.every().day.at("06:00").do(self.daily_report_job)
        schedule.every().sunday.at("06:00").do(self.weekly_report_job)
        schedule.every(1).month.at("06:00").do(self.monthly_report_job)

        thread = threading.Thread(target=self.run_schedule_loop, daemon=True)
        thread.start()

    def run_schedule_loop(self):
        """
        Continuously run scheduled tasks.
        """
        while True:
            schedule.run_pending()
            time.sleep(30)

    def hands_off_job(self):
        print(f"[{datetime.now()}] Running hands-off job...")
        self.hands_off_controller.run_hands_off()

    def daily_report_job(self):
        print(f"[{datetime.now()}] Sending daily email report...")
        self.email_sender.send_daily_report()

    def weekly_report_job(self):
        print(f"[{datetime.now()}] Sending weekly email report...")
        self.email_sender.send_weekly_report()

    def monthly_report_job(self):
        print(f"[{datetime.now()}] Sending monthly email report...")
        self.email_sender.send_monthly_report()
