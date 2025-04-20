# config_manager.py

import configparser
import os

class ConfigManager:
    """
    ConfigManager handles the configuration settings for the application.
    It loads settings from a configuration file (config.ini) or creates one with default values.
    """
    def __init__(self, config_file: str = "config.ini"):
        """
        Initialize the ConfigManager with the specified config file.
        :param config_file: Path to the configuration file.
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        """
        Loads the configuration from the config file.
        If the file does not exist, creates a default configuration.
        """
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.create_default_config()

    def create_default_config(self):
        """
        Creates a default configuration file with sample settings.
        """
        self.config['Amazon'] = {
            'access_key': 'YOUR_ACCESS_KEY',
            'secret_key': 'YOUR_SECRET_KEY',
            'partner_tag': 'YOUR_PARTNER_TAG'
        }
        self.config['Telegram'] = {
            'bot_token': 'YOUR_TELEGRAM_BOT_TOKEN',
            'group_ids': 'GROUP_ID1, GROUP_ID2'
        }
        self.config['WhatsApp'] = {
            'cookies': 'YOUR_WHATSAPP_COOKIES'
        }
        self.config['Scheduler'] = {
            'scraping_frequency': '6',  # in hours
            'daily_report_time': '06:00',
            'weekly_report_day': 'Sunday',
            'monthly_report_day': '1'
        }
        self.config['General'] = {
            'hands_off_mode': 'False'
        }
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_amazon_config(self) -> dict:
        """
        Retrieves the Amazon configuration settings.
        :return: A dictionary of Amazon settings.
        """
        return dict(self.config['Amazon'])

    def get_telegram_config(self) -> dict:
        """
        Retrieves the Telegram configuration settings.
        :return: A dictionary of Telegram settings.
        """
        return dict(self.config['Telegram'])

    def get_whatsapp_config(self) -> dict:
        """
        Retrieves the WhatsApp configuration settings.
        :return: A dictionary of WhatsApp settings.
        """
        return dict(self.config['WhatsApp'])

    def get_scheduler_config(self) -> dict:
        """
        Retrieves the Scheduler configuration settings.
        :return: A dictionary of Scheduler settings.
        """
        return dict(self.config['Scheduler'])

    def get_general_config(self) -> dict:
        """
        Retrieves the General configuration settings.
        :return: A dictionary of general settings.
        """
        return dict(self.config['General'])

    def update_config(self, section: str, key: str, value: str):
        """
        Updates a specific configuration setting and writes the changes to the config file.
        :param section: The section in the configuration file.
        :param key: The key within the section.
        :param value: The new value to set.
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def get_email_config(self):
        return self.config.get("email", {})
