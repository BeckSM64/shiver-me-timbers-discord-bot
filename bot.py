#!/usr/bin/env python3
import os
import discord
import datetime
import re
from os.path import join, dirname
from dotenv import load_dotenv
from discord.ext import commands
from discord.ext import tasks
from discord import Member

# Read in .env for discord token
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await messageMonitorLoop.start()

@tasks.loop(seconds=1)
async def messageMonitorLoop():

    # Loop through guilds to which the bot belongs
    for guild in bot.guilds:

        # TODO: Loop through text channels in guild
        # Check most recent message for 4chan webm link
        pass

bot.run(TOKEN)
