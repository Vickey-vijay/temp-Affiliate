# run_scheduler.py

from scheduler import Scheduler
from config_manager import ConfigManager
from notification_publisher import NotificationPublisher
from publisher import Publisher
from handsoff_mode_controller import HandsOffModeController
from price_monitor import PriceMonitor
import pymongo

def main():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["ramesh"]
    published_collection = client["published_data"]["products"]

    config_manager = ConfigManager()
    amazon_config = config_manager.get_amazon_config()


    notification_publisher = NotificationPublisher(config_manager)
    publisher = Publisher(db, published_collection, notification_publisher)
    hands_off_controller = HandsOffModeController(
        db["products"], published_collection, notification_publisher
    )
    price_monitor = PriceMonitor(db["products"], amazon_config=config_manager.get_amazon_config())

    scheduler = Scheduler(
        db["products"],
        published_collection,
        notification_publisher,
        hands_off_controller,
        config_manager
    )

    scheduler.add_job(price_monitor.monitor_products, trigger="interval", hours=config.get("scraping_frequency_in_hours", 6))
    scheduler.add_job(hands_off_controller.process_and_publish, trigger="interval", hours=config.get("scraping_frequency_in_hours", 6))
    scheduler.add_job(publisher.send_scheduled_report, trigger="cron", hour=6)
    scheduler.add_job(lambda: publisher.send_scheduled_report(period="weekly"), trigger="cron", day_of_week="sun", hour=6)
    scheduler.add_job(lambda: publisher.send_scheduled_report(period="monthly"), trigger="cron", day=1, hour=6)

    print("✅ Background scheduler running...")
    # scheduler.run()

if __name__ == "__main__":
    main()
