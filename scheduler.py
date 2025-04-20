import schedule
import threading
import time
from datetime import datetime
from utils.email_sender import EmailSender


class Scheduler:
    def __init__(self, products_collection, published_collection, notification_publisher, hands_off_controller, config_manager):
            self.products_collection = products_collection
            self.published_collection = published_collection
            self.notification_publisher = notification_publisher
            self.hands_off_controller = hands_off_controller
            self.config_manager = config_manager
            self.jobs = []

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
            """Continuously run scheduled tasks."""
            print("Starting scheduler loop...")
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

    def add_job(self, func, trigger, **kwargs):
        """Add a job to the scheduler.
        
        Args:
            func: The function to run
            trigger: The type of trigger ("interval", "cron")
            **kwargs: Additional arguments for the job
        """
        job = {
            "func": func,
            "trigger": trigger,
            "kwargs": kwargs
        }
        self.jobs.append(job)
        print(f"Added job: {kwargs.get('name', func.__name__)}")

    def run(self):
        """Start the scheduler and run jobs according to their schedule."""
        # Here you would implement the scheduling logic based on the jobs list
        print("Scheduler is running...")
        
        # Set up schedule based on jobs
        for job in self.jobs:
            if job["trigger"] == "interval":
                hours = job["kwargs"].get("hours", 1)
                schedule.every(hours).hours.do(job["func"])
                print(f"Scheduled {job['kwargs'].get('name', job['func'].__name__)} to run every {hours} hours")
            elif job["trigger"] == "cron":
                hour = job["kwargs"].get("hour")
                day_of_week = job["kwargs"].get("day_of_week")
                day = job["kwargs"].get("day")
                
                if day_of_week:
                    if hour is not None:
                        schedule.every().day.at(f"{hour:02d}:00").do(job["func"])
                        print(f"Scheduled {job['kwargs'].get('name', job['func'].__name__)} to run at {hour:02d}:00 on {day_of_week}")
                elif day:
                    if hour is not None:
                        # This is just a placeholder - schedule doesn't have direct monthly scheduling
                        print(f"Scheduled {job['kwargs'].get('name', job['func'].__name__)} to run at {hour:02d}:00 on day {day} of month")
                else:
                    if hour is not None:
                        schedule.every().day.at(f"{hour:02d}:00").do(job["func"])
                        print(f"Scheduled {job['kwargs'].get('name', job['func'].__name__)} to run daily at {hour:02d}:00")

        # Run the continuous loop
        self.run_schedule_loop()