from enum import Enum, auto
import formatter
import discord
import re
from collections import OrderedDict


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    SELECT_SPAM = auto()
    SELECT_OFFENSIVE = auto()
    SELECT_HARASSMENT = auto()
    SELECT_ILLEGAL = auto()
    SELECT_IMMINENT = auto()
    ASK_TO_BLOCK_SENDER = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    SPAM_KEYWORD = "spam"
    OFFENSIVE_KEYWORD = "offensive content"
    HARASSMENT_KEYWORD = "harassment"
    ILLEGAL_KEYWORD = "illegal content"
    DANGER_KEYWORD = "imminent danger"
    BULLYING_KEYWORD = "bullying"
    UNWANTED_SEXUAL_KEYWORD = "unwanted sexual content"
    PRIVITE_KEYWORD = "revealing private information"
    HATE_SPEECH_KEYWORD = "hate speech targeting me"

    def __init__(self, client, mod_channel, reporter_id):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_message = None
        self.report_message_link = None
        self.reporter_id = reporter_id
        self.mod_channel = mod_channel
        self.report_flow = ""

    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                self.report_message_link = message.content
                message = await channel.fetch_message(int(m.group(3)))
                self.report_message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            reply = "I found this message: ```" + \
                message.author.name + ": " + message.content + "```\n"
            reply += "Select your reason for reporting this message:\n"
            reply += f"  `{Report.SPAM_KEYWORD}`\n"
            reply += f"  `{Report.OFFENSIVE_KEYWORD}`\n"
            reply += f"  `{Report.HARASSMENT_KEYWORD}`\n"
            reply += f"  `{Report.ILLEGAL_KEYWORD}`\n"
            reply += f"  `{Report.DANGER_KEYWORD}`\n"
            return [reply]

        if self.state == State.MESSAGE_IDENTIFIED:
            if (Report.SPAM_KEYWORD in message.content):
                self.state = State.REPORT_COMPLETE
                self.report_flow += Report.SPAM_KEYWORD
                await self.send_mod_message()
                return ["Thank you for helping to keep our platform safe. We will investigate this report. "]
            if (Report.OFFENSIVE_KEYWORD in message.content):
                self.state = State.REPORT_COMPLETE
                self.report_flow += Report.OFFENSIVE_KEYWORD
                await self.send_mod_message()
                return ["Thank you for reporting. We will investigate to determine whether this content violates our policies. "]
            if (Report.HARASSMENT_KEYWORD in message.content):
                self.state = State.SELECT_HARASSMENT
                self.report_flow += f"{Report.HARASSMENT_KEYWORD}"
                reply = "Thank you for reporting. What type of harassment is this? \n"
                reply += f"  `{Report.BULLYING_KEYWORD}`\n"
                reply += f"  `{Report.UNWANTED_SEXUAL_KEYWORD}`\n"
                reply += f"  `{Report.PRIVITE_KEYWORD}`\n"
                reply += f"  `{Report.HATE_SPEECH_KEYWORD}`\n"
                return [reply]
            if (Report.ILLEGAL_KEYWORD in message.content):
                self.state = State.REPORT_COMPLETE
                self.report_flow += Report.ILLEGAL_KEYWORD
                await self.send_mod_message()
                return ["Thank you for reporting. We will investigate to determine whether this content warrants removal and/or referral to law enforcement. "]
            if (Report.DANGER_KEYWORD in message.content):
                self.state = State.REPORT_COMPLETE
                self.report_flow += Report.DANGER_KEYWORD
                await self.send_mod_message()
                return ["Thank you for reporting. We take threats to people’s safety very seriously and our moderation team will review this report. If you believe you are in immediate danger, you should also contact local law enforcement."]
            return ["Wrong input. Please select the reason again."]

        if self.state == State.SELECT_HARASSMENT:
            replies = []
            keywords = [Report.BULLYING_KEYWORD, Report.UNWANTED_SEXUAL_KEYWORD,
                        Report.PRIVITE_KEYWORD, Report.HATE_SPEECH_KEYWORD]
            harass_type = next(
                (kw for kw in keywords if kw in message.content), "")
            if (len(harass_type) > 0):
                self.report_flow += f" -> {harass_type}"
                replies.append(
                    "Thank you for reporting. We will investigate to determine whether this content warrants removal and/or referral to law enforcement.")
                replies.append(
                    "Would you like to hide messages from this sender (Reply `Yes`/`No`)? They will not know this has happened.")
                self.state = State.ASK_TO_BLOCK_SENDER
            else:
                replies.append(
                    "Wrong input. Please select the type of harassment again.")
            return replies

        if self.state == State.ASK_TO_BLOCK_SENDER:
            self.state = State.REPORT_COMPLETE
            if ("y" in message.content.lower()):
                self.report_flow += f" -> block sender"
                await self.send_mod_message()
                return ["This sender is blocked! (simulated blocking)\n Thank you for reporting. We will investigate to determine whether this content warrants removal and/or referral to law enforcement. If you would like, refer to the mental health resources below: https://covid19.ca.gov/resources-for-emotional-support-and-well-being/ "]
            else:
                self.report_flow += f" -> not block sender"
                await self.send_mod_message()
                return ["Thank you for reporting. We will investigate to determine whether this content warrants removal and/or referral to law enforcement. \nIf you would like, refer to the mental health resources below: https://covid19.ca.gov/resources-for-emotional-support-and-well-being/"]
        return []

    async def send_mod_message(self):
        mod_message = self.get_report_information()
        await self.mod_channel.send(formatter.format_dict_to_str(mod_message))

    def get_report_information(self):
        mod_message = OrderedDict()
        mod_message['reporter'] = self.reporter_id
        mod_message['author'] = self.report_message.author.id
        mod_message['message'] = self.report_message.content
        mod_message['link'] = self.report_message_link
        mod_message['metadata'] = f'Report Flow is `{self.report_flow}`'
        return mod_message

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
