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
guild_id_to_lists_of_webms_dict = {}


def doesTextChannelExist(guild):

    found_text_channel = False
    for temp_channel in guild.text_channels:
        if "webm-archive" in temp_channel.name:
            found_text_channel = True
            break
    return found_text_channel

def isFileNameInList(list_of_webms, file_name_to_compare):

    # Return false if the list is empty
    if list_of_webms is None:
        return False

    # Check if file name exists in list
    found_file_name = False
    for file_name in list_of_webms:
        if file_name == file_name_to_compare:
            found_file_name = True
            break

    return found_file_name


@bot.event
async def on_message(message):

    # message content
    content = message.content

    # message author
    user = message.author

    # text channel message originated on
    channel = message.channel

    # check if message is a 4chan webm link
    if ( message is not None) and ("https://i.4cdn.org" in message.content) and (".webm" in message.content):
        # Create url link
        # TODO: This won't work if a 4chan link is posted with no space
        # between previous text and the link (ie. laksdjflaksdjhttps://i.4cdn.org )
        # Could fix this in the future but I don't really care
        message_content_array = message.content.split()
        for split_message in message_content_array:
            if "https://i.4cdn.org" in split_message:
                url_link = split_message

        # Get filename to download from url link
        file_name = message.content.split('/')[-1]

        # List of webms that have already been archived
        list_of_webms = guild_id_to_lists_of_webms_dict.get(message.guild.id)

        # Check if newly posted webm was previously archived
        if isFileNameInList(list_of_webms, file_name) is False:

            # Check to see if webm-archive text channel exists
            # and if not, create it
            found_text_channel = doesTextChannelExist(message.guild)

            if found_text_channel is False:
                await message.guild.create_text_channel("webm-archive")

            # Get archive channel
            webm_archive_channel = discord.utils.get(message.guild.text_channels, name="webm-archive")

            # Download webm from url
            urllib.request.urlretrieve(url_link, file_name)

            # Keep track of the file that was downloaded to avoid duplicates
            if guild_id_to_lists_of_webms_dict.get(message.guild.id) is None:
                guild_id_to_lists_of_webms_dict[message.guild.id] = [file_name]
            else:
                guild_id_to_lists_of_webms_dict[message.guild.id].append(file_name)

            # Upload file to webm archive channel
            await webm_archive_channel.send(file=discord.File('./' + file_name))

            # Remove webm that was downloaded
            os.remove(os.path.join("./", file_name))

bot.run(TOKEN)
