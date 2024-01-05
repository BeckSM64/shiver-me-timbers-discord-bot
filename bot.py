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


bot.run(TOKEN)
