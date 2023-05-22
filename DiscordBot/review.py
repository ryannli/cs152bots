# This class enables moderators to review both manually and automatically reported messages.

from enum import Enum, auto
import discord
import formatter
from collections import OrderedDict
import re

class State(Enum):
    REVIEW_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    CONTENT_IS_ALLOWED = auto()
    CONTENT_IS_MAYBE_ALLOWED = auto()
    CONTENT_IS_NOT_ALLOWED = auto()
    AWAITING_IMMINENT_DANGER_MESSAGE = auto()
    REVIEW_COMPLETED = auto()

class Review:
    START_KEYWORD = "review"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client
        self.auto_reported = None
        self.reported_message = None
        self.review_flow = ""
        self.message_info = None
        self.valid_report = None

    async def handle_message(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REVIEW_COMPLETED
            return ["Review cancelled."]
        
        if self.state == State.REVIEW_START:
            reply =  "Thank you for starting the review process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to review.\n"
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
                return ["I cannot help you review messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
                self.reported_message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            self.state = State.MESSAGE_IDENTIFIED
            self.review_flow += "review has been started ->"
            self.message_info = formatter.unformat_str_to_dict(message.content)

            reply = "I found this message: ```" + self.message_info['author'] + ": " + self.message_info['message'] + "```\n"
            reply += "Please make a determination below:\n"
            reply += f"  `1: Content does not violate policies.`\n"
            reply += f"  `2: Content might violate policies.`\n"
            reply += f"  `3: Content does violate policies.`\n"
            return [reply]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if '1' in message.content:
                self.review_flow += "reviewer #1 says content is allowed ->"
                self.state = State.CONTENT_IS_ALLOWED
            if '2' in message.content:
                self.review_flow += "reviewer #1 is unsure about content ->"
                self.state = State.CONTENT_IS_MAYBE_ALLOWED
            if '3' in message.content:
                self.review_flow += "review #1 says content is not allowed ->"
                self.state = State.CONTENT_IS_NOT_ALLOWED

        if self.state == State.CONTENT_IS_MAYBE_ALLOWED:
            if 'reviewer #2 is asked their opinion' in self.review_flow:
                if 'a' in message.content.lower():
                    self.review_flow += "reviewer #2 says content is allowed ->"
                    self.state = State.CONTENT_IS_ALLOWED
                if 'b' in message.content.lower():
                    self.review_flow += "reviewer #2 says content is not allowed ->"
                    self.state = State.CONTENT_IS_NOT_ALLOWED
            else:
                self.review_flow += "reviewer #2 is asked their opinion on uncertain content ->"
                reply = "Please contact a team member and let them review the post."
                reply += "Please enter their determination below:\n"
                reply += f"  `A: Content does not violate policies.`\n"
                reply += f"  `B: Content does violate policies.`\n"
                return [reply]

        if self.state == State.CONTENT_IS_ALLOWED:
            self.review_flow += "content is allowed, check for adverserial reporting"
            self.state = State.REVIEW_COMPLETED
            self.valid_report = False
            return []
        
        if self.state == State.CONTENT_IS_NOT_ALLOWED:
            self.review_flow += "author must be banned and post removed ->"
            self.state = State.AWAITING_IMMINENT_DANGER_MESSAGE
            self.valid_report = True
            
            reply = "Should local authorities be called?\n"
            reply += f"  `Y: Content is illegal or threatens imminent harm.`\n"
            reply += f"  `N: Content is not illegal and does not threaten imminent harm.`\n"
            return [reply]

        # After content has been deemed to go against policies, need to make sure
        # that serious threats and imminent danger to people are reported to police.
        if self.state == State.AWAITING_IMMINENT_DANGER_MESSAGE:
            if 'y' in message.content.lower():
                self.state = State.REVIEW_COMPLETED
                self.review_flow += "police should be contacted"
                return []
            if 'n' in message.content.lower():
                self.state = State.REVIEW_COMPLETED
                self.review_flow += "police should not be contacted"
                return []
        
        return ["Wrong input. Please select the reason again."]
    
    def review_complete(self):
        return self.state == State.REVIEW_COMPLETED
    
    def get_review_information(self):
        review_information = OrderedDict()
        review_information['reporter'] = self.message_info['reporter']
        review_information['author'] = self.message_info['author']
        review_information['message'] = self.message_info['message']
        review_information['link'] = self.message_info['link']
        review_information['metadata'] = self.review_flow_to_string()
        review_information['violated'] = self.valid_report
        return review_information
    
    def review_flow_to_string(self):
        # The review_flow isn't complete if the review was canceled, rather then completed.
        if self.review_flow.endswith("->"):
            return "Review canceled."
        parts = self.review_flow.split("->")
        reply =  "Your review of the following message is complete: ```" + self.message_info['author'] + ": " + self.message_info['message'] + "```\n"
        step = 1
        for part in parts:
            reply += f"{step}:  `{part}`\n"
            step += 1
        return reply