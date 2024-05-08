import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

import configparser
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage
from kik_unofficial.datatypes.xmpp.errors import LoginError
import kik_unofficial.datatypes.xmpp.chatting as chatting
from typing import NoReturn
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KikBot(KikClientCallback):
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.username, self.password = self.load_credentials()
        self.client = KikClient(self, self.username, self.password)

    def load_credentials(self) -> tuple:
        config = configparser.ConfigParser()
        config.read(self.config_path)
        username = config.get('credentials', 'username')
        password = config.get('credentials', 'password')
        return username, password

    def on_authenticated(self) -> NoReturn:
        logging.info("Bot has been authenticated successfully!")

    def on_chat_message_received(self, chat_message: IncomingChatMessage) -> NoReturn:
        logging.info(f"Received a message from {chat_message.from_jid}: {chat_message.body}")

    # Called if login fails for any reason including requiring a captcha
    def on_login_error(self, login_error: LoginError):
        logging.error(f"Failed to login: {login_error.message}")
        if login_error.is_captcha():
            logging.info(f"Captcha solving required: {login_error.captcha_url}")
            login_error.solve_captcha_wizard(self.client)


# Usage
if __name__ == '__main__':
    bot = KikBot('config.ini')
