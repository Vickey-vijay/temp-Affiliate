# utils/whatsapp_sender.py

import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

class WhatsappSender:
    def __init__(self, cookie_file="whatsapp_cookies.json"):
        self.cookie_file = cookie_file
        self.driver = self._start_driver()

    def _start_driver(self):
        options = Options()
        options.add_argument("--user-agent=Mozilla/5.0")
        options.add_argument("--headless")  # Remove this line if you want to see browser
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(options=options)
        driver.get("https://web.whatsapp.com")

        # Load cookies to stay logged in
        try:
            with open(self.cookie_file, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(5)
            print("✅ WhatsApp cookies loaded successfully.")
        except Exception as e:
            print("⚠️ Failed to load WhatsApp cookies. Please login manually and save them.")
        return driver

    def send_message(self, product_data):
        """
        Sends message to a group or contact using previously stored cookies.
        """
        try:
            message = (
                f"*{product_data['product_name']}*\n"
                f"💰 *Current Price:* ₹{product_data['price']}\n"
                f"💸 *MRP:* ₹{product_data.get('mrp', 'N/A')}\n"
                f"🛒 {product_data['product_url']}"
            )

            # Define the contact or group name to send the message to
            group_name = "Your Group Name"  # 🔁 Change this or get it from config

            # Search and click on group
            search_box = self.driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            search_box.clear()
            search_box.send_keys(group_name)
            time.sleep(2)

            group = self.driver.find_element(By.XPATH, f'//span[@title="{group_name}"]')
            group.click()
            time.sleep(2)

            # Type and send message
            input_box = self.driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            input_box.send_keys(message)
            send_button = self.driver.find_element(By.XPATH, '//button[@data-testid="compose-btn-send"]')
            send_button.click()
            print("✅ WhatsApp message sent.")

        except Exception as e:
            print(f"❌ WhatsApp message failed: {e}")

    def save_cookies(self):
        """
        Save cookies to avoid login again.
        """
        cookies = self.driver.get_cookies()
        with open(self.cookie_file, "w") as f:
            json.dump(cookies, f)
        print("✅ WhatsApp cookies saved.")

    def close(self):
        self.driver.quit()
