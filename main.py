import configparser
import os
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage, IncomingGroupChatMessage
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse
from kik_unofficial.datatypes.xmpp.errors import LoginError
import kik_unofficial.datatypes.xmpp.chatting as chatting
from typing import NoReturn
import logging
from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id
import asyncio
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class KikBot(KikClientCallback):
    def __init__(self):
        self.load_config()
        latest_captcha_result_path = 'latest_captcha_result.txt'
        self.latest_captcha_result_contents = None
        if os.path.exists(latest_captcha_result_path):
            with open(latest_captcha_result_path, 'r') as f:
                self.latest_captcha_result_contents = f.read()
                logging.info(f"Loaded latest captcha result.")
        if self.latest_captcha_result_contents is None:
            logging.info("No latest captcha result found.")

        #some_random_device_id = random_device_id()
        #some_random_android_id = random_android_id()

        self.client = KikClient(callback=self,
                                kik_username=self.username,
                                kik_password=self.password,
                                device_id=self.device_id,
                                android_id=self.android_id)
        self.on_peer_info_received_response: PeersInfoResponse = None
        self.admin_pics = {}

    def load_config(self):
        config = configparser.ConfigParser()
        config_path = os.path.abspath('config.ini')
        config.read(config_path)
        self.username = config.get('credentials', 'username')
        self.password = config.get('credentials', 'password')
        self.admin_usernames = [username.strip() for username in config.get('admin', 'usernames').split(',')]
        self.device_id = config.get('device', 'device_id')
        self.android_id = config.get('device', 'android_id')
        logging.info(f"Loaded config file: {config_path}")

    async def start(self):
        await self.client.login(username=self.username,
                                password=self.password,
                                captcha_result=self.latest_captcha_result_contents)

    def on_authenticated(self) -> NoReturn:
        logging.info("Bot has been authenticated successfully!")
        # get the admin info
        self.get_admin_info()
        logging.info(f"Got admin info: {self.admin_pics}")

    def get_admin_info(self):
        logging.info(f"Getting admin info for {self.admin_usernames}")
        for admin_username in self.admin_usernames:
            # Request information
            self.client.request_info_of_username(admin_username)
            logging.info(f"Requested info for {admin_username}")

            # Wait for response, meaning on_peer_info_received() gets called, and self.on_peer_info_received_response is no longer None
            while self.on_peer_info_received_response is None:
                asyncio.sleep(1)

            self.admin_pics[admin_username] = self.on_peer_info_received_response.users[0].pic

        logging.info(f"Admin pics: {self.admin_pics}")
        return

    def on_peer_info_received(self, response: PeersInfoResponse):
        logging.info(f"Received peer info: {response.users[0]}")
        self.on_peer_info_received_response = response

    # Called if login fails for any reason including requiring a captcha
    def on_login_error(self, login_error: LoginError):
        logging.error(f"Failed to login: {login_error.message}")
        if login_error.is_captcha():
            logging.info(f"Captcha solving required: {login_error.captcha_url}")
            login_error.solve_captcha_wizard(self.client)

    def on_image_received(self, response: chatting.IncomingImageMessage):
        logging.info(f"Received an image message from {response.from_jid}")

    def on_group_message_received(self, chat_message: IncomingGroupChatMessage):
        """
        Only gets called when a text message is received in a group chat. Does not get called for media.
        :param chat_message:
        :return:
        """
        logging.info(f"Received a group message from {chat_message.from_jid}: {chat_message.body}")

        is_troll_message = False

        # is_troll_message = ((chat_message.from_jid == "uvymq6qm2mlvy7dm4fa2ettadghi5xutrqhoh2d4lrfd7h75gcna_a@talk.kik.com") or
        #                     ("test_troll_message" in chat_message.body and chat_message.from_jid == self.admin_jid_group))

        if is_troll_message:
            outbound_message = f"Please block/ignore this troll. This chat is currently un-moderated, go to #VrChatFurr for a moderated chat."
            self.client.send_chat_message(chat_message.group_jid, outbound_message)

        # if ("command" in chat_message.body and chat_message.from_jid == self.admin_jid_group):
        #     self.handle_command(command=chat_message.body, is_admin=True, from_jid=chat_message.from_jid, group_jid=chat_message.group_jid)

        from_user_info = self.client.request_info_of_users(peer_jids=[chat_message.from_jid])
        return

    def on_chat_message_received(self, chat_message: IncomingChatMessage) -> NoReturn:
        logging.info(f"Received a DM from {chat_message.from_jid}: {chat_message.body}")

        # if "command" in chat_message.body and chat_message.from_jid == self.admin_jid_dm:
        #     self.handle_command(command=chat_message.body, is_admin=True, from_jid=chat_message.from_jid, group_jid=None)

    def handle_command(self, command: str, is_admin: bool, from_jid: str, group_jid: str = None):
        logging.info(f"Handling command: {command}. Is admin: {is_admin}. From JID: {from_jid}. Group JID: {group_jid}")

        if is_admin and "add_as_friend" in command and not group_jid:
            logging.info(f"Adding {from_jid} as a friend.")
            self.client.add_friend(peer_jid=from_jid)
            self.client.send_chat_message(from_jid, f"Added you as a friend.")

        if is_admin and "send_message" in command and group_jid:
            # message_to_send will be everything after "send_message" in the command
            logging.info(f"Sending message to group {group_jid}")
            message_to_send = command.split("send_message")[1].strip()
            self.client.send_chat_message(peer_jid=group_jid, message=message_to_send)

        pass


# Usage
if __name__ == '__main__':
    bot = KikBot()