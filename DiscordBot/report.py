from enum import Enum, auto
import discord
import re

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
    BLOCK_SENDER_IDENTIFIED = auto()


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

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
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
            reply =  "Thank you for starting the reporting process. "
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
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            reply = "I found this message: ```" + message.author.name + ": " + message.content + "```\n"
            reply += "Select your reason for reporting this message:\n"
            reply += f"  `{Report.SPAM_KEYWORD}`\n"
            reply += f"  `{Report.OFFENSIVE_KEYWORD}`\n"
            reply += f"  `{Report.HARASSMENT_KEYWORD}`\n"
            reply += f"  `{Report.ILLEGAL_KEYWORD}`\n"
            reply += f"  `{Report.DANGER_KEYWORD}`\n"
            return [reply]
        
        if self.state == State.MESSAGE_IDENTIFIED:
            if (Report.SPAM_KEYWORD in message.content):
                self.state = State.SELECT_SPAM
                return ["Thank you for helping to keep our platform safe. We will investigate this report. "]
            if (Report.OFFENSIVE_KEYWORD in message.content):
                self.state = State.SELECT_OFFENSIVE
                return ["Thank you for reporting. We will investigate to determine whether this content violates our policies. "]
            if (Report.HARASSMENT_KEYWORD in message.content):
                self.state = State.SELECT_HARASSMENT
                reply = "Thank you for reporting. What type of harassment is this? \n"
                reply += f"  `{Report.BULLYING_KEYWORD}`\n"
                reply += f"  `{Report.UNWANTED_SEXUAL_KEYWORD}`\n"
                reply += f"  `{Report.PRIVITE_KEYWORD}`\n"
                reply += f"  `{Report.HATE_SPEECH_KEYWORD}`\n"
                return [reply]
            if (Report.ILLEGAL_KEYWORD in message.content):
                self.state = State.SELECT_ILLEGAL
                return ["Thank you for reporting. We will investigate to determine whether this content warrants removal and/or referral to law enforcement. "]
            if (Report.DANGER_KEYWORD in message.content):
                self.state = State.SELECT_IMMINENT
                return ["Thank you for reporting. We take threats to people’s safety very seriously and our moderation team will review this report. If you believe you are in immediate danger, you should also contact local law enforcement."]
            return ["Wrong input. Please select the reason again."]
        
        if self.state == State.SELECT_HARASSMENT:
            replies = []
            if (Report.BULLYING_KEYWORD in message.content or Report.UNWANTED_SEXUAL_KEYWORD in message.content or 
                Report.PRIVITE_KEYWORD in message.content or Report.HATE_SPEECH_KEYWORD in message.content):
                replies.append("Thank you for reporting. We will investigate to determine whether this content warrants removal and/or referral to law enforcement.")
                replies.append("Would you like to hide messages from this sender (Reply `Yes`/`No`)? They will not know this has happened.")
                self.state = State.ASK_TO_BLOCK_SENDER
            else:
                replies.append("Wrong input. Please select the type of harassment again.")
            return replies

        if self.state == State.ASK_TO_BLOCK_SENDER:
            if ("Yes" in message.content):
                self.state = State.BLOCK_SENDER_IDENTIFIED
                return ["This sender is blocked! (simulated blocking)"]
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    


    

