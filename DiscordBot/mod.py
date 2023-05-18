# This class enables moderators to take actions to both manually and automatically reported messages.

from enum import Enum, auto
import discord
import re

class State(Enum):
    REVIEW_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    CONTENT_IS_NOT_HARASSMENT = auto()
    CONTENT_IS_MAYBE_HARASSMENT = auto()
    CONTENT_IS_HARASSMENT = auto()
    REVIEW_COMPLETED = auto()

class Mod:
    START_KEYWORD = "review"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, mod_channel):
        self.state = State.REVIEW_START
        self.client = client
        self.auto_reported = None
        self.reported_message = None
        self.mod_channel = mod_channel
        self.review_flow = ""

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
            # Need to be within the moderator channel!
            print(channel)
            try:
                message = await channel.fetch_message(int(m.group(3)))
                self.reported_message = message
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            
            self.state = State.MESSAGE_IDENTIFIED
            self.review_flow += "review of '" + message.content + "' has been started ->"
            reply = "I found this message: ```" + message.author.name + ": " + message.content + "```\n"
            reply += "Please make a determination below:\n"
            reply += f"  `1: Content is not harassment and does not violate policies.`\n"
            reply += f"  `2: Content might be harassment / violate policies.`\n"
            reply += f"  `3: Content is harassment and does violate policies.`\n"
            return [reply]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if '1' in message.content:
                self.review_flow += "reviewer #1 says content is not harassment ->"
                self.state = State.CONTENT_IS_NOT_HARASSMENT
            if '2' in message.content:
                self.review_flow += "reviewer #1 is unsure about content ->"
                self.state = State.CONTENT_IS_MAYBE_HARASSMENT
            if '3' in message.content:
                self.review_flow += "review #1 says content is harassment ->"
                self.state = State.CONTENT_IS_HARASSMENT

        if self.state == State.CONTENT_IS_MAYBE_HARASSMENT:
            if 'reviewer #2 is asked their opinion' in self.review_flow:
                if 'a' in message.content.lower():
                    self.review_flow += "reviewer #2 says content is not harassment ->"
                    self.state = State.CONTENT_IS_NOT_HARASSMENT
                if 'b' in message.content.lower():
                    self.review_flow += "reviewer #2 says content is harassment ->"
                    self.state = State.CONTENT_IS_HARASSMENT
            else:
                self.review_flow += "reviewer #2 is asked their opinion on uncertain content -> "
                reply = "Please contact a team member and let them review the post."
                reply += "Please enter their determination below:\n"
                reply += f"  `A: Content is not harassment and does not violate policies.`\n"
                reply += f"  `B: Content is harassment and does violate policies.`\n"
                return [reply]
        if self.state == State.CONTENT_IS_HARASSMENT:
            self.review_flow += "author must be banned and post removed"
            self.state = State.REVIEW_COMPLETE
            return [self.reported_message, self.review_flow]
        if self.state == State.CONTENT_IS_NOT_HARASSMENT:
            self.review_flow += "content is not harassment, check for adverserial reporting"
            self.state = State.REVIEW_COMPLETE
            return [self.reported_message, self.review_flow]
        
        return ["Wrong input. Please select the reason again."]
    
    def get_state_of_review(self):
        return self.state