#!/usr/bin/env python3
import os
import discord
import urllib.request
import asyncio

from os.path import join, dirname
from dotenv import load_dotenv
from discord.ext import commands

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


#TODO: rename this. it does more than simply convert.
async def username_to_id(ctx, user_name):
    # determine which user the bot should find in the voice channels
    if user_name is None:
        member_to_look_for = ctx.author.id # if no @ was provided to the command
    else:
        try:
            # strip special characters out of the member id
            member_to_look_for = int(user_name.replace('@', '').replace('<', '').replace('>', ''))
        except:
            # send an error message to the text channel for invalid input to the commands
            await ctx.send("Please @ a valid member of the server")
            return

    return member_to_look_for

@bot.command()
async def influence(ctx, arg=None):
    """ saves a user's mp3 file, named as their user_id """
    
    user_name = arg
    user_id = await username_to_id(ctx, user_name)

    if str(ctx.message.attachments) == "[]": # Checks if there is an attachment on the message
        return
    else: # If there is it gets the filename from message.attachments
        split_v1 = str(ctx.message.attachments).split("filename='")[1]
        filename = str(split_v1).split("' ")[0]
        if filename.endswith(".mp3"): # Checks if it is a .mp3 file
            await ctx.message.attachments[0].save(fp="audio/users/{}".format(str(user_id) + ".mp3")) # saves the file


@bot.command()
async def love(ctx, arg=None):
    """ plays an audio file associated with a user's id  """
    
    user_name = arg
    user_id = await username_to_id(ctx, user_name)
    file_path = "audio/users/" + str(user_id)  + ".mp3"
    await playAudio(ctx, file_path, ctx.author.id)


@bot.command()
async def hug(ctx, arg=None):
    """Calls the playAudio() function with the 1hugaday audio"""

    file_path = "audio/1hugaday.mp3"
    user_name = arg
    user_id = await username_to_id(ctx, user_name)
    await playAudio(ctx, file_path, user_id)


@bot.command()
async def shiver(ctx, arg=None):
    """Calls the playAudio() function with the shivermetimbers audio"""

    file_path = "audio/shivermetimbers.mp3"
    user_name = arg
    user_id = await username_to_id(ctx, user_name)
    await playAudio(ctx, file_path, user_id)


async def playAudio(ctx, file_path, member_to_look_for):
    """
    Bot will join the VC and play an audio clip
    ripped from the original shiver me timbers video
    """

    # check if file exists
    if not os.path.isfile(file_path):
        return
        

    # get list of voice channels in the server the message was posted in
    list_of_voice_channels_in_server = ctx.guild.voice_channels

    # iterate over voice channels
    for voice_channel in list_of_voice_channels_in_server:

        # iterate over members in current voice channel
        for member in voice_channel.members:

            # check if the author of the message is in the currrent voice channel
            if member_to_look_for == member.id:

                # if they are, have the bot join the VC and play the hug audio
                # if not already connected to VC
                if not is_connected(ctx):
                    vc = await voice_channel.connect()
                    vc.play(discord.FFmpegPCMAudio(source=file_path))
                    vc.pause()
                    await asyncio.sleep(1)
                    vc.resume()
                    while vc.is_playing():
                        await asyncio.sleep(1)
                    await vc.disconnect()


def isMessageA4ChanWebm(message):
    """Returns True if message contains a link to a 4chan webm"""
    return ( message is not None) and (("https://i.4cdn.org" in message.content) or ("https://is2.4chan.org" in message.content)) and (".webm" in message.content)


def getUrlFromMessage(message):
    """Splits the message and returns the URL"""

    # TODO: This won't work if a 4chan link is posted with no space
    # between previous text and the link (ie. laksdjflaksdjhttps://i.4cdn.org )
    message_content_array = message.content.split()
    for split_message in message_content_array:
        if ("https://i.4cdn.org" in split_message) or ("https://is2.4chan.org" in split_message):
            url_link = split_message

    return url_link


async def createWebmArchiveChannel(message):
    """Creates a webm archive channel if one doesn't already exist"""

    # Check to see if webm-archive text channel exists
    found_text_channel = doesTextChannelExist(message.guild)

    if found_text_channel is False:
        await message.guild.create_text_channel("webm-archive")


def getTextChannelByName(message, text_channel_name):
    """return text channel that matches name that was passed in"""
    text_channel = discord.utils.get(message.guild.text_channels, name=text_channel_name)
    return text_channel


@bot.event
async def on_message(message):

    # required to process commmands when overriding on_message function
    await bot.process_commands(message)

    # check if message is a 4chan webm link
    if isMessageA4ChanWebm(message):

        # Create url link
        url_link = getUrlFromMessage(message)

        # Get filename to download from url link
        file_name = url_link.split('/')[-1]

        # List of webms that have already been archived
        list_of_webms = guild_id_to_lists_of_webms_dict.get(message.guild.id)

        # Check if newly posted webm was previously archived
        if isFileNameInList(list_of_webms, file_name) is False:

            # Create webm archive channel for server if it doesn't already exist
            await createWebmArchiveChannel(message)

            # Get archive channel
            webm_archive_channel = getTextChannelByName(message, "webm-archive")

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
