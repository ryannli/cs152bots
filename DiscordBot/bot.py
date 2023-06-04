# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
import openai_utils
import formatter 
import editdistance
from report import Report
from review import Review
import pdb
import profanity_check
from collections import OrderedDict
import argparse


# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']

banned_words_path = 'data/badwords.txt'

with open(banned_words_path) as f:
    banned_words = set()
    for line in f:
        banned_words.add(line.strip())

class ModBot(discord.Client):
    def __init__(self, use_openai=False, debug=False): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild

        self.inprogress_reports = {} # Map from user IDs to the state of their in-progress report
        self.inprogress_reviews = {} # Map from user IDs to the state of their in-progress reviews

        self.completed_reports = [] # All completed reports
        self.completed_reviews = [] # All completed reviews

        self.banned_reporters = [] # All people banned due to making false reports
        self.banned_posters = [] # All people banned due to violating content policies

        self.mods = [1029345335748857917, 811498139017412608] # user IDs that are allowed to post / review messages in mod channel. 3q
        self.use_openai = use_openai
        self.debug = debug

        self.regexes_to_ban = [] # Regex list that should not be allowed on the server.

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.\n')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                    # A hack since we only use one mod channel
                    self.single_mod_channel = channel

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return
        
        # For development purposes. Write 'debug' to print out the state of attributes witihn bot.py
        if message.content == 'debug':
            print()
            print("IN STATUS REPORTS -----------------------------------")
            for id in self.inprogress_reports:
                print(f"ID Of Reporter: {id}")
                print(f"Pending Report: {self.inprogress_reports[id]}")
            print()

            print("IN STATUS REVIEWS ----------------------------------")
            for id in self.inprogress_reviews:
                print(f"ID Of Reviewer: {id}")
                print(f"Pending Review: {self.inprogress_reviews[id]}")
            print()

            print("COMPLETED REPORTS ----------------------------------")
            for report in self.completed_reports:
                print(report)
            print()

            print("COMPLETED REVIEWS ----------------------------------")
            for review in self.completed_reviews:
                print(review)
            print()

            print("BANNED DUE TO FALSE REPORTS ----------------------")
            for id in self.banned_reporters:
                print(id)
            print()

            print("BANNED DUE TO CONTENT ----------------------------")
            for id in self.banned_posters:
                print(id)
            print()

            await message.delete()
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_message_edit(self, before, after):
        print(f"{before.author.name} edited a previously sent message.")
        print(f"The old message: '{before.content}'")
        print(f"The new message: '{after.content}'\n")
        await self.on_message(after)
        
    async def handle_dm(self, message):
        print(f"The discord bot has detected a new dm from {message.author.name}")
        print(f"The message content: '{message.content}' \n")

        await self.report_flow(message)

    async def handle_channel_message(self, message):
        print(f"The discord bot has detected a new message from {message.author.name} in {message.guild.name}")
        print(f"The message content: '{message.content}' \n")

        if message.author.id in self.banned_posters:
            await message.delete()
            await message.channel.send(f"{message.author.name} is banned due to violating content policies.")
            return

        if message.author.id in self.banned_reporters:
            await message.delete()
            await message.channel.send(f"{message.author.name} is banned due to making false reports.")
            return

        # Anyone can post within this channel. Note that messages in this channel can be 
        # manually or automatically reported. Once reported, those messages are forwarded
        # to the moderator channel for review.
        if message.channel.name == f'group-{self.group_num}':

            for banned_regex in self.regexes_to_ban:
                if re.fullmatch(banned_regex, message.content):
                    await message.channel.send(f"{message.content} is not allowed. It matches a banned regex.\n")
                    await message.delete()
                    return

            await self.automatic_detection_flow(message)
            await self.report_flow(message)
        
        # Only mods can post within this channel. Note that besides the messages posted by mods,
        # this channel will contain all the reported messages that were forwarded either manually
        # or automatically.
        if message.channel.name == f'group-{self.group_num}-mod':
            # Uncommented this if you want to only allow mods to post in this channel
            # if message.author.id not in self.mods:
            #     print(f"{message.author.name} is not a moderator. Their message was deleted.")
            #     await message.delete()
            #     await message.channel.send(f"{message.author.name} is not a moderator. Their message was deleted.")
            #     return


            # Mods are able to ban regex words by specifying: BAN: SOMETHING
            if message.content.startswith("BAN:"):
                regex_to_ban = message.content[4:]

                try:
                    pattern = re.compile(regex_to_ban)
                    self.regexes_to_ban.append(pattern)
                    reply =  f"The regex '{regex_to_ban}' is no longer allowed on the server.\n"
                    await message.channel.send(reply)
                except re.error:
                    await message.channel.send("Malformated regex")
                return
            
            await self.review_flow(message)
            
            # If a review process was completed, we can detect a user making false reports.
            # (user has made several reports, which all have been deemed as not breaking content policies)
            self.check_false_reports()

            # If a review process was compelted, we can detect a user with multiple reports against him
            # (user has repeatedly posted content which have been deemed to break content policies).
            self.check_past_violations()

    async def review_flow(self, message):
        ''''
        Flow responsible for the review process (in mod channel).
        '''

        # Handle a help message
        if message.content == Review.HELP_KEYWORD:
            reply =  "Use the `review` command to begin the review process.\n"
            reply += "Use the `cancel` command to cancel the review process.\n"
            await message.channel.send(reply)
            return
    
        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a review flow
        if author_id not in self.inprogress_reviews and not message.content.startswith(Review.START_KEYWORD):
            return

        # If we don't currently have an active review for this user, add one
        if author_id not in self.inprogress_reviews:
            self.inprogress_reviews[author_id] = Review(self)

        # Let the moderator class handle this message; forward all the messages it returns to us
        responses = await self.inprogress_reviews[author_id].handle_message(message)

        if self.inprogress_reviews[author_id].review_complete():
            review_information = self.inprogress_reviews[author_id].get_review_information()
            review_flow = review_information['metadata']

            self.inprogress_reviews.pop(author_id)
            await message.channel.send(review_flow) 

            # If review was canceled, then we don't need to update anything.
            if 'Review canceled' in review_flow:
                return

            self.completed_reviews.append(review_information)
        else: 
            for r in responses:
                await message.channel.send(r)

    def check_false_reports(self):
        ''''
        Users who have made 3+ false reports need to be banned from the server. 
        '''
        user_id_to_false_reports = {}
        for review in self.completed_reviews:
            if not review['violated']:
                reporter_id = review['reporter']

                if reporter_id not in user_id_to_false_reports:
                    user_id_to_false_reports[reporter_id] = 0

                user_id_to_false_reports[reporter_id] += 1

        for user_id in user_id_to_false_reports:
            if user_id_to_false_reports[user_id] >= 3:
                if user_id not in self.banned_reporters:
                    self.banned_reporters.append(int(user_id))
                    print(f"{user_id} has made 3+ false reports. They are banned.\n")

    def check_past_violations(self):
        ''''
        Users who have made 3+ posts that violated content policies need to be banned from the server.
        '''
        user_id_to_true_reports = {}
        for review in self.completed_reviews:
            if review['violated']:
                author_id = review['author']

                if author_id not in user_id_to_true_reports:
                    user_id_to_true_reports[author_id] = 0

                user_id_to_true_reports[author_id] += 1

        for user_id in user_id_to_true_reports:
            if user_id_to_true_reports[user_id] >= 3:
                if user_id not in self.banned_posters:
                    self.banned_posters.append(int(user_id))
                    print(f"{user_id} has made 3+ posts that violated content policies. They are banned.\n")


    async def report_flow(self, message):
        ''''
        Flow responsible for the report process (in main channel).
        '''

        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.inprogress_reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.inprogress_reports:
            self.inprogress_reports[author_id] = Report(self, self.single_mod_channel, author_id)

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.inprogress_reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.inprogress_reports[author_id].report_complete():
            report_information = self.inprogress_reports[author_id].get_report_information()
            
            if not self.inprogress_reports[author_id].report_was_canceled():
                report_information = self.inprogress_reports[author_id].get_report_information()
                self.completed_reports.append(report_information)
            
            self.inprogress_reports.pop(author_id)

    async def auto_delete_message(self, message):
        await message.delete()
        await message.channel.send(f'Deleted offensive message from {message.author.name}. Please be respectful for community guidelines.')
    async def auto_report_message(self, message, metadata):
        mod_channel = self.mod_channels[message.guild.id]
        mod_message = OrderedDict()
        mod_message['reporter'] = "SYSTEM AUTOMATIC"
        mod_message['priority'] = 2
        mod_message['author'] = message.author.id
        mod_message['message'] = message.content
        mod_message['link'] = message.jump_url
        mod_message['metadata'] = metadata
        await mod_channel.send(formatter.format_dict_to_str(mod_message))

    async def automatic_detection_flow(self, message):
        ''''
        Flow responsible for detecting harmful messages (automatically).
        '''
        # TODO: Cleanup profanity score codings if no longer needed. 

        if self.use_openai:
            openai_scores = openai_utils.get_openai_dict_scores(message.content)
            if (self.debug):
                await message.channel.send(f'Debugging Info: Message received as `{message.content}`. {self.openai_score_format(openai_scores)}')
            # Number of categories that have a score of at least 4 (scale 1-5)
            score_at_least_4_count = sum(1 for value in openai_scores.values() if value >= 4)
            # Number of categories that have a score of at least 3 (scale 1-5)
            score_at_least_3_count = sum(1 for value in openai_scores.values() if value >= 3)

            message_auto_reported = False
            message_auto_deleted = False

            if (score_at_least_4_count >=2):
                message_auto_deleted = True
                await self.auto_delete_message(message)
            elif (score_at_least_3_count >= 1):
                message_auto_reported = True
                await self.auto_report_message(message, self.openai_score_format(openai_scores))

            # If openAI has not detected any problems that merit auto report or auto deletion, then
            # double check by also manually checking for malicious spacing and intentional misspellings.
            if not message_auto_deleted and not message_auto_reported:
                scores = self.get_profanity_score(self.sanitize_malicious_input(message.content))

                # Blatantly harmful messages don't need to be reviewed. "fuck you" is an example of such a message.
                if (scores > 0.95):
                    await self.auto_delete_message(message)

                # Ambigious messages need to be reviewed. "I hate that" is an example of such a message.
                elif (scores > 0.4):
                    await self.auto_report_message(message, self.profanity_score_format("{:.2f}".format(scores)))
        else:
            scores = self.get_profanity_score(self.sanitize_malicious_input(message.content))

            # Blatantly harmful messages don't need to be reviewed. "fuck you" is an example of such a message.
            if (scores > 0.95):
                await self.auto_delete_message(message)

            # Ambigious messages need to be reviewed. "I hate that" is an example of such a message.
            elif (scores > 0.4):
                await self.auto_report_message(message, self.profanity_score_format("{:.2f}".format(scores)))

    def sanitize_malicious_input(self, raw_message):
        '''
        There are alot of ways that people can bypass automatic detection. This is an attempt to limit some of those
        ways. For example, people can intentionally mispell words, add random spacing between characters, etc...
        '''

        # handle words with malicious spacing between -> 'f u   c k' = 'fuck'
        raw_message_single_spaces = re.sub(' +', ' ', raw_message)

        all_single_characters = True
        for word in raw_message_single_spaces.split(" "):
            if len(word) > 1:
                all_single_characters = False

        if all_single_characters:
            raw_message_no_spaces = re.sub(' +', '', raw_message)
            return raw_message_no_spaces

        # handle words that are intentionally mispelled
        for word in raw_message_single_spaces.split(" "):
            for banned_word in banned_words:
                if editdistance.eval(word, banned_word) <= 1:
                    # fuk you man -> fuck -> triggers automatic detection of sentence
                    return banned_word

        return raw_message

    def get_profanity_score(self, message):
        return profanity_check.predict_prob([message])[0]

    
    def openai_score_format(self, openai_dict):
        return "OpenAI detected harmful score (scale 1-5) is \n" + formatter.format_dict_to_str(openai_dict)
    
    def profanity_score_format(self, text):
        return "profanity check score is " + text


def main(args):
    print("OpenAI flag:", args.openai)
    print("Debug flag:", args.openai)
    client = ModBot(args.openai, args.debug)
    client.run(discord_token)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="discord bot args parser")

    parser.add_argument("-openai", "--openai", type=bool, help="If use OpenAI to automatically detect harmful messages")
    parser.add_argument("-debug", "--debug", type=bool, help="If use debugging mode. It will send additional messages in Discord")

    args = parser.parse_args()
    main(args)