import configparser
import os
from kik_unofficial.client import KikClient
from kik_unofficial.callbacks import KikClientCallback
from kik_unofficial.datatypes.xmpp.chatting import IncomingChatMessage, IncomingGroupChatMessage
from kik_unofficial.datatypes.xmpp.roster import FetchRosterResponse, PeersInfoResponse
from kik_unofficial.datatypes.xmpp.errors import LoginError
import kik_unofficial.datatypes.xmpp.chatting as chatting
from typing import NoReturn , List, Union
import logging
from kik_unofficial.utilities.credential_utilities import random_device_id, random_android_id
import asyncio
import time
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_async_task(coroutine):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Create a new loop since one does not exist in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # This is important: Start the loop in this thread
        threading.Thread(target=loop.run_forever).start()

    # Ensure the coroutine is scheduled in the right loop
    asyncio.run_coroutine_threadsafe(coroutine, loop)


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
        self.info_event = asyncio.Event()
        self.admin_pics = {}
        self.non_admin_user_jids = []

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
        # Schedule get_admin_info coroutine without blocking
        asyncio.create_task(self.get_admin_info())
        logging.info(f"Got admin info: {self.admin_pics}")

    async def get_admin_info(self):
        logging.info(f"Getting admin info for {self.admin_usernames}")
        for admin_username in self.admin_usernames:
            await self.get_info_of_username(admin_username)
            pic = self.on_peer_info_received_response.users[0].pic
            if not pic:
                logging.warning(f"No pic found for {admin_username}, authentication will not work.")
            self.admin_pics[admin_username] = pic

        logging.info(f"Admin pics: {self.admin_pics}")

    async def get_info_of_username(self, username: str) -> PeersInfoResponse:
        self.client.request_info_of_username(username)
        logging.info(f"Requested info for username {username}")
        await self.info_event.wait()
        logging.info(f"on_peer_info_received() info_event set after calling get_info_of_username()")
        self.info_event = asyncio.Event()
        return self.on_peer_info_received_response

    async def get_info_of_users(self, peer_jids: Union[str, List[str]]) -> PeersInfoResponse:
        self.client.request_info_of_users(peer_jids)
        logging.info(f"Requested info for peer jids: {peer_jids}")

        # Wait for on_peer_info_received to be called
        await self.info_event.wait()


        logging.info(f"on_peer_info_received() info_event set after calling get_info_of_users()")
        self.info_event = asyncio.Event()
        return self.on_peer_info_received_response

    def on_peer_info_received(self, response: PeersInfoResponse):
        logging.info(f"Received peer info for users: {response.users}")
        self.on_peer_info_received_response = response
        self.info_event.set()  # Set the event to resume get_admin_info

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

        send_troll_message_needed = (chat_message.from_jid == "uvymq6qm2mlvy7dm4fa2ettadghi5xutrqhoh2d4lrfd7h75gcna_a@talk.kik.com")
        if send_troll_message_needed:
            logging.info(f"Sending troll message to {chat_message.group_jid} because the sender is a troll.")
            self.send_troll_message(group_jid=chat_message.group_jid)

        if "command" in chat_message.body:
            # asyncio.create_task(self.handle_command(command=chat_message.body, from_jid=chat_message.from_jid, group_jid=chat_message.group_jid))
            run_async_task(self.handle_command(command=chat_message.body, from_jid=chat_message.from_jid,
                                               group_jid=chat_message.group_jid))

        return

    def send_troll_message(self, group_jid: str):
        outbound_message = f"Please block/ignore this troll. This chat is currently un-moderated, go to #VrChatFurr for a moderated chat."
        self.client.send_chat_message(group_jid, outbound_message)

    def on_chat_message_received(self, chat_message: IncomingChatMessage) -> NoReturn:
        logging.info(f"Received a DM from {chat_message.from_jid}: {chat_message.body}")

        if "command" in chat_message.body:
            # asyncio.create_task(self.handle_command(command=chat_message.body, from_jid=chat_message.from_jid))
            run_async_task(self.handle_command(command=chat_message.body, from_jid=chat_message.from_jid))

    async def get_admin_username_from_jid(self, jid: str):
        """
        :param jid:
        :return: A string of the matching admin username if found, otherwise None
        """

        if jid in self.non_admin_user_jids:
            logging.warning(f"JID {jid} is in non_admin_user_jids. Returning None.")
            return None

        await self.get_info_of_users([jid])

        user_pic = self.on_peer_info_received_response.users[0].pic
        matched_admin_username = None
        for admin_username, admin_pic in self.admin_pics.items():
            if admin_pic == user_pic:
                matched_admin_username = admin_username
                break

        if matched_admin_username is None:
            self.non_admin_user_jids.append(jid)
            logging.warning(f"Could not find matching admin username for JID {jid}. "
                            f"Added to non_admin_user_jids. Non-admin JIDs: {self.non_admin_user_jids}"
                            f" ({len(self.non_admin_user_jids)} total).")

        return matched_admin_username

    async def handle_command(self, command: str, from_jid: str, group_jid: str = None):
        logging.info(f"Handling command: {command}. From JID: {from_jid}. Group JID: {group_jid}")

        admin_username = await self.get_admin_username_from_jid(from_jid)

        logging.info(f"Admin username: {admin_username}")

        if admin_username and "add_as_friend" in command and not group_jid:
            logging.info(f"Adding {from_jid} as a friend.")
            self.client.add_friend(peer_jid=from_jid)
            self.client.send_chat_message(from_jid, f"Added you as a friend.")

        if admin_username and "send_message" in command and group_jid:
            # message_to_send will be everything after "send_message" in the command
            logging.info(f"Sending message to group {group_jid}")
            message_to_send = command.split("send_message")[1].strip()
            self.client.send_chat_message(peer_jid=group_jid, message=message_to_send)

        if admin_username and "send_troll_message" in command and group_jid:
            logging.info(f"Sending troll message to group {group_jid}")
            self.send_troll_message(group_jid=group_jid)

        pass


# Usage
if __name__ == '__main__':
    bot = KikBot()