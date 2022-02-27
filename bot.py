#!/usr/bin/env python3
import os
import discord
import datetime
import re
import urllib.request

from os.path import join, dirname
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext import tasks
from discord import Member

# Read in .env for discord token
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup bot
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary of guild ids to list of previously downloaded webms
guild_id_to_webm_dict = {}

@bot.event
async def on_ready():
    await messageMonitorLoop.start()

@tasks.loop(seconds=1)
async def messageMonitorLoop():

    # Loop through guilds to which the bot belongs
    for guild in bot.guilds:

        # Loop through text channels in guild
        for channel in guild.text_channels:

            # Check most recent message for 4chan webm link
            if channel.last_message_id is not None:
                print(channel.last_message_id)

                # Try/catch to deal with the most recent message being deleted
                try:
                    message = (await channel.fetch_message(channel.last_message_id))
                except:
                    message = None
                if ( message is not None) and ("https://i.4cdn.org" in message.content) and (".webm" in message.content):

                    # Create url link
                    url_link = message.content

                    # Get filename to download from url link
                    file_name = message.content.split('/')[-1]

                    if guild_id_to_webm_dict.get(guild.id) != file_name:
                        # Download webm from url
                        urllib.request.urlretrieve(url_link, file_name)

                        # Keep track of the file that was downloaded to avoid duplicates
                        guild_id_to_webm_dict[guild.id] = file_name
                        await channel.send(file=discord.File('./' + file_name))


bot.run(TOKEN)
