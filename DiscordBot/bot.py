# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
import pdb
import profanity_check

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


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reviews = {} # Map from user IDs to the state of their reviews
        self.mods = [1029345335748857917] # user IDs that are allowed to post / review messages in mod channel. 3q

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

        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self, self.single_mod_channel)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        print(f"The discord bot has detected a new message from {message.author.name} in {message.guild.name}")
        print(f"The message content: '{message.content}' \n")

        # Anyone can post within this channel. Note that messages in this channel can be 
        # manually or automatically reported. Once reported, those messages are forwarded
        # to the moderator channel for review.
        if message.channel.name == f'group-{self.group_num}':

            scores = self.eval_text(message.content)
            
            # Blatantly harmful messages don't need to be reviewed. "fuck you" is an example of such a message.
            if (scores > 0.95):
                await message.delete()
                await message.channel.send(f'Deleted offensive message from {message.author.name}. Please be respectful for community guidelines.')

            # Ambigious messages need to be reviewed. "I hate that" is an example of such a message.
            elif (scores > 0.4):
                mod_channel = self.mod_channels[message.guild.id]
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                await mod_channel.send(self.code_format("{:.2f}".format(scores)))

            # TODO: Users need to be able to trigger the report flow from the group-21 channel. Currently,
            # users are only able to trigger the report flow from DMs (as seen in handle_dm())
        
        # Only mods can post within this channel. Note that besides the messages posted by mods,
        # this channel will contain all the reported messages that were forwarded either manually
        # or automatically.
        if message.channel.name == f'group-{self.group_num}-mod':
            if message.author.id not in self.mods:
                print(f"{message.author.name} is not a moderator. Their message was deleted.")
                await message.delete()
                return
            
            author_id = message.author.id
            responses = []

            # Only respond to messages if they're part of a review flow
            if author_id not in self.reviews and not message.content.startswith(Review.START_KEYWORD):
                return

            # If we don't currently have an active review for this user, add one
            if author_id not in self.reviews:
                self.reviews[author_id] = Review(self)

            # Let the moderator class handle this message; forward all the messages it returns to us
            responses = await self.reviews[author_id].handle_message(message)

            # Note that the final response is just the message that was reviewed.
            # Thus, we can't print out the message object, we need to print out the review flow.
            if self.reviews[author_id].review_complete():
                review_flow = self.reviews[author_id].review_flow_to_string()

                # We only want to send a review flow that was completed (not one that was partially completed, but
                # then the user canceled the review).
                if review_flow:
                    await message.channel.send(review_flow)   
                self.reviews.pop(author_id)
            else: 
                for r in responses:
                    await message.channel.send(r)
    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return profanity_check.predict_prob([message])[0]

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "profanity_check score: '" + text + "'"


client = ModBot()
client.run(discord_token)