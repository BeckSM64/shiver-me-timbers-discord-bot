#!/usr/bin/env python3
import os
import logging
import datetime
import time
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

# Dictionary to track user's cooldown times from previously played intro
user_cooldown_times_dict = {}

# constants
AUDIO_DIR = "audio/"
USERS_DIR = "users/"
USER_AUDIO_DIR = AUDIO_DIR + USERS_DIR

log = logging.getLogger()
log.setLevel(logging.INFO)


def is_connected(ctx):
    """Returns True if bot is already connected to VC"""
    return discord.utils.get(bot.voice_clients, guild=ctx.guild)

@bot.event
async def on_voice_state_update(member, before, after):
    """Plays a user's soundclip when joining a voice channel. 10 hour cooldown"""
    global user_cooldown_times_dict

    # ensure member is entering (not exiting), and is not the bot
    if not before.channel and after.channel and member.id is not bot.user.id:
        logging.info('{} is what it do'.format(member.name))

        # check that enough cooldown time has elapsed before replaying intro sound
        prev_time = user_cooldown_times_dict.get(member.id)
        cooldown_time = datetime.timedelta(hours=10)

        # proceed if this is the first time the member's entered, or if cooldown has expired
        if not prev_time or datetime.datetime.now() > (prev_time + cooldown_time):
            user_cooldown_times_dict[member.id] = datetime.datetime.now()
            logging.info('{} has joined the vc'.format(member.nick))
            file_path = getUserMp3(member.id)
            await playAudio(file_path, after.channel)
        else:
            delta_time = prev_time + cooldown_time - datetime.datetime.now()
            logging.info('{} intro will not play for another {} hours and {} minutes'.format(member.nick, delta_time.seconds//3600, (delta_time.seconds//60)%60))



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
    else: # If there is an attachment, get the filename from message.attachments
        split_v1 = str(ctx.message.attachments).split("filename='")[1]
        filename = str(split_v1).split("' ")[0]
        if filename.endswith(".mp3"):
            #   save the file in a user's directory,
            # and then symlink to it using the user's id
            user_new_file_path = str(user_id) + "/" + filename
            user_new_symlink = USER_AUDIO_DIR + str(user_id) + ".mp3"
            if not os.path.exists(USER_AUDIO_DIR + str(user_id)):
                os.mkdir(USER_AUDIO_DIR + str(user_id));
            await ctx.message.attachments[0].save(fp=USER_AUDIO_DIR + user_new_file_path)
   
            #    create the symlink to the new file
            # (create a temp symlink, and rename to allow overwriting existing files)
            os.symlink(user_new_file_path, user_new_symlink + ".tmp")
            os.rename(user_new_symlink + ".tmp", user_new_symlink)


def getUserMp3(user_id):
    """ finds the user's custom mp3, or the default mp3 """

    file_path = AUDIO_DIR + "default.mp3"
    user_file_path = USER_AUDIO_DIR + str(user_id) + ".mp3"
    if os.path.isfile(user_file_path):
        file_path = user_file_path 
    return file_path

@bot.command()
async def love(ctx, arg=None):
    """ plays an audio file associated with a user's id  """
    
    user_name = arg
    user_id = await username_to_id(ctx, user_name)
    file_path = getUserMp3(user_id)
    await spoolAudio(ctx, file_path, ctx.author.id)

async def playAudio(file_path, voice_channel):
    logging.info("playing: " + file_path)
    vc = await voice_channel.connect()
    vc.play(discord.FFmpegPCMAudio(source=file_path))
    vc.pause()
    await asyncio.sleep(1)
    vc.resume()
    while vc.is_playing():
        await asyncio.sleep(1)
    await vc.disconnect()


async def spoolAudio(ctx, file_path, member_to_look_for):
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
                    print("shouldnt be running this right now")
                    await playAudio(file_path, voice_channel)

bot.run(TOKEN)
