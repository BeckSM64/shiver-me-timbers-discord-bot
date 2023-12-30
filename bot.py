#!/usr/bin/env python3
import os
import discord
import datetime
import re
import urllib.request
import asyncio

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


def is_connected(ctx):
    """Returns True if bot is already connected to VC"""
    return discord.utils.get(bot.voice_clients, guild=ctx.guild)


@bot.command()
async def hug(ctx):
    """
    Bot will join the VC that the user who ran the command is currently in
    and play an audio clip ripped from the original shiver me timbers video
    """

    # get list of voice channels in the server the message was posted in
    list_of_voice_channels_in_server = ctx.guild.voice_channels

    # iterate over voice channels
    for voice_channel in list_of_voice_channels_in_server:

        # iterate over members in current voice channel
        for member in voice_channel.members:

            # check if the author of the message is in the currrent voice channell
            if ctx.author.id == member.id:

                # if they are, have the bot join the VC and play the hug audio
                # if not already connected to VC
                if not is_connected(ctx):
                    vc = await voice_channel.connect()
                    vc.play(discord.FFmpegPCMAudio(source="audio/1hugaday.mp3"))
                    while vc.is_playing():
                        await asyncio.sleep(1)
                    await vc.disconnect()


@bot.event
async def on_message(message):

    # required to process commmands when overriding on_message function
    await bot.process_commands(message)

    # message content
    content = message.content

    # message author
    user = message.author

    # text channel message originated on
    channel = message.channel

    # check if message is a 4chan webm link
    # TODO: check for other valid urls (ie 4cdn.org, 4chan.org, etc.)
    if ( message is not None) and (("https://i.4cdn.org" in message.content) or ("https://is2.4chan.org" in message.content)) and (".webm" in message.content):
        # Create url link
        # TODO: This won't work if a 4chan link is posted with no space
        # between previous text and the link (ie. laksdjflaksdjhttps://i.4cdn.org )
        # Could fix this in the future but I don't really care
        message_content_array = message.content.split()
        for split_message in message_content_array:
            if ("https://i.4cdn.org" in split_message) or ("https://is2.4chan.org" in split_message):
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
