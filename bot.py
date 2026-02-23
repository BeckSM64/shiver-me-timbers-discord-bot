#!/usr/bin/env python3
import os
import math
import subprocess
import discord
import requests
import asyncio
import cloudscraper
import yt_dlp

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


def does_text_channel_exist(guild):
    """
    Checks to see if a webm archive text channel already exists

    Args:
        guild: The ID of the server

    Returns:
        bool: Whether the webm archive text channel was found or not
    """

    found_text_channel = False
    for temp_channel in guild.text_channels:
        if "webm-archive" in temp_channel.name:
            found_text_channel = True
            break
    return found_text_channel


def is_file_name_in_list(list_of_webms, file_name_to_compare):
    """
    Checks to see if file name is in the list of videos that have already
    been posted to this discord server

    Args:
        list_of_webms: List of webms that have already been posted
        file_name_to_compare: Filename of video currently being posted

    Returns:
        bool: Whether or not video has been posted already in server
    """

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

def is_message_a_reddit_video_link(message):
    """
    Returns True if message contains a reddit or old.reddit url

    Args:
        message: Latest Discord text channel message

    Returns:
        bool: Whether or not the message contains a 4chan video link
   
    """
    if (
        message is not None and
        ("reddit" in message.content)
       ):
        print(message.content + " is a reddit url")
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                url = get_url_from_message(message)
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            if "entries" in info:
                info = next(iter(info["entries"]), None)
                if info is None:
                    return False
            return info.get("vcodec") not in (None, "none")

def is_message_a_4chan_video_link(message):
    """
    Returns True if message contains a link to a 4chan webm or mp4

    Args:
        message: Latest Discord text channel message

    Returns:
        bool: Whether or not the message contains a 4chan video link
    """
    return (
        (message is not None)
        and (
            ("https://i.4cdn.org" in message.content)
            or ("https://is2.4chan.org" in message.content)
        )
        and (".webm" in message.content or ".mp4" in message.content)
    )


def get_url_from_message(message):
    """
    Splits the message and returns the URL

    Args:
        message: Latest Discord text channel message

    Returns:
        str: The URL as a string
    """

    # TODO: This won't work if a 4chan link is posted with no space
    # between previous text and the link (ie. laksdjflaksdjhttps://i.4cdn.org )
    message_content_array = message.content.split()
    for split_message in message_content_array:
        if (
            ("4cdn" in split_message) or
            ("4chan" in split_message) or
            ("reddit" in split_message)
            ):
            url_link = split_message
    
    return url_link


async def create_webm_archive_channel(message):
    """
    Creates a webm archive channel if one doesn't already exist

    Args:
        message: Latest Discord text channel message

    Returns:
        None
    """

    # Check to see if webm-archive text channel exists
    found_text_channel = does_text_channel_exist(message.guild)

    if found_text_channel is False:
        await message.guild.create_text_channel("webm-archive")


def get_text_channel_by_name(message, text_channel_name):
    """
    Gets the text channel by name

    Args:
        message: Discord text channel message
        text_channel_name: Name of text channel

    Returns:
        TextChannel: Returns a text channel object corresponding to provided name
    """
    text_channel = discord.utils.get(message.guild.text_channels, name=text_channel_name)
    return text_channel


def download_video_via_cloudscraper(url_link) -> bool:
    """
    Handles the download attemp from 4chan using cloud scraper

    Args:
        url_link: Link to the 4chan webm/mp4

    Returns:
        bool: Result of the download attempt
    """

    result = False # Overwrite if we succeed

    try:
        # Create a CloudScraper instance with Cloudflare bypass capabilities
        scraper = cloudscraper.create_scraper()

        print(f"Attempting to download with cloudscraper from: {url_link}")

        # Make the GET request. cloudscraper will try to solve any CAPTCHAs
        response = scraper.get(url_link, stream=True)
        response.raise_for_status() # This will raise an exception for 4xx/5xx responses

        # Print cloudscraper http response
        print(f"\n--- Cloudscraper Response Details ---")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")

        # Ensure the page being access is a video that can be downloaded
        if 'video' in response.headers.get('Content-Type', ''):
            filename = url_link.split('/')[-1].split('?')[0]
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Video downloaded successfully as {filename}!")
            result = True
        else:
            print(f"Cloudscraper got a {response.status_code} but Content-Type was not 'video'.")
            print(f"Response content (first 500 chars): {response.text[:500]}")
            print("\nCloudscraper might have failed to bypass, or the content is not a video.")

    # Catch HTTP errors and other exceptions
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.reason}")
        print(f"Response content (if available): {e.response.text[:500]}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Cloudscraper Attempt Complete ---")
    return result


#downloaded_files
def download_video_via_yt_dlp(url_link) -> (bool, str):
    """
    Handles the download attemp from reddit using yt_dlp

    Args:
        url_link: Link to the reddit video

    Returns:
        tuple (bool, str)
        bool: Result of the download attempt
        str: Downloaded filepath
    """

    #  This hook is given to yt_dlp so that it will provide us
    # the filenames when it completes the downloads
    # but because the final video and audio files still need
    # to be merged, these filenames end up being less useful
    # but the way that this hook works is too cool to delete.
    # and, more importantly, for files that are downloaded
    # but are too large for discord's 10mb limit, we may want
    # to use these two files with ffmpeg directly to convert
    # to webm. Probably won't though. Easier to run ffpmeg on
    # the final .mp4, convert, and try the upload with that webm
    #
    # def hook(d):
    #     if d['status'] == 'finished':
    #         downloaded_files.append(d['filename'])

    # These options are used to perform the reddit download
    ydl_opts = {
            'verbose': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4', # this allows us to download a png
            'noplaylist': True,
            'http_headers': {'Accept': '*/*'}, # ai: Workaround for some Reddit URL issues
            #'progress_hooks': [hook], #this hook allows us to find the intermediate files
        }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download the video along with ydl info, which provides the filename
            info = ydl.extract_info(url_link, download=True)
            final_filename = info.get("filepath") or ydl.prepare_filename(info)
            print("final filename: " + final_filename)
            return (True, final_filename)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return (False, "")

@bot.event
async def on_message(message):
    """
    Discord API event driven method that runes when a message

    Args:
        message: Latest Discord text channel message

    Returns:
        None
    """

    # required to process commmands when overriding on_message function
    await bot.process_commands(message)

    # check if message is a 4chan webm link
    if is_message_a_4chan_video_link(message):

        # Create url link
        url_link = get_url_from_message(message)

        # Get filename to download from url link
        file_name = url_link.split('/')[-1]

        # List of webms that have already been archived
        list_of_webms = guild_id_to_lists_of_webms_dict.get(message.guild.id)

        # Check if newly posted webm was previously archived
        if is_file_name_in_list(list_of_webms, file_name) is False:

            # Create webm archive channel for server if it doesn't already exist
            await create_webm_archive_channel(message)

            # Get archive channel
            webm_archive_channel = get_text_channel_by_name(message, "webm-archive")

            # Attempt to download the video
            result = download_video_via_cloudscraper(url_link)

            # Only keep track of the file if it downloaded successfully
            if result:
                # Keep track of the file that was downloaded to avoid duplicates
                if guild_id_to_lists_of_webms_dict.get(message.guild.id) is None:
                    guild_id_to_lists_of_webms_dict[message.guild.id] = [file_name]
                else:
                    guild_id_to_lists_of_webms_dict[message.guild.id].append(file_name)

                # Upload file to webm archive channel
                await webm_archive_channel.send(file=discord.File('./' + file_name))

                # Remove webm that was downloaded
                os.remove(os.path.join("./", file_name))

    if is_message_a_reddit_video_link(message):
        print(message.content + " is a video from reddit")

        # Create url link
        #   removing trailing slash to make it easier
        #   to split for the 'already archived' dict
        url_link = get_url_from_message(message).rstrip('/')

        #  Get media name to download from url link
        # this name is not the final filename, but we will use
        # it for the list_of_webmbs_dict. The final filename
        # will not be known until the download is complete
        url_psudo_name = url_link.split('/')[-2] + '/' + url_link.split('/')[-1]
        print("will retrieve video from" + url_psudo_name)

        # List of webms that have already been archived
        list_of_webms = guild_id_to_lists_of_webms_dict.get(message.guild.id)

        # Check if newly posted webm was previously archived
        if is_file_name_in_list(list_of_webms, url_psudo_name) is False:

            # Create webm archive channel for server if it doesn't already exist
            await create_webm_archive_channel(message)

            # Get archive channel
            webm_archive_channel = get_text_channel_by_name(message, "webm-archive")

            # Attempt to download the video
            # result contains (bool, filename)
            result = download_video_via_yt_dlp(url_link)

            # Only keep track of the file if it downloaded successfully
            if result[0]:
                # Keep track of the file that was downloaded to avoid duplicates
                if guild_id_to_lists_of_webms_dict.get(message.guild.id) is None:
                    guild_id_to_lists_of_webms_dict[message.guild.id] = [url_psudo_name]
                else:
                    guild_id_to_lists_of_webms_dict[message.guild.id].append(url_psudo_name)

                file_name = result[1]
                file_size = os.path.getsize(file_name);

                MAX_VIDEO_SIZE_MB = 10
                MAX_VIDEO_SIZE_KB = MAX_VIDEO_SIZE_MB * 1024
                MAX_VIDEO_SIZE_BYTES = MAX_VIDEO_SIZE_KB * 1024
                MAX_VIDEO_SIZE_BITS = MAX_VIDEO_SIZE_BYTES * 8
 
                MAX_DISCORD_FILESIZE = MAX_VIDEO_SIZE_BYTES

                if (file_size > MAX_DISCORD_FILESIZE):
                    print(f"downloaded file too large: {file_size}")
                    await message.channel.send(content=f"file {file_name} is {file_size} large. Downsizing to {MAX_VIDEO_SIZE_MB}MB. This will take some time. TODO: is this isngle threaded? will this block other uploads? let's find out.")
    
                    duration_command = ["ffprobe", "-v", "error", "-show_entries",
                                        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                                        file_name]
                    video_duration = int(math.ceil(float(subprocess.check_output(duration_command))))
                    print(f"duration is: {video_duration} seconds")

                    #let's force 128kb/s audio
                    target_audio_bitrate = 128000

                    # BITS = 10 * 1024 * 1024 * 8
                    target_video_bitrate = int(MAX_VIDEO_SIZE_BITS / video_duration)
                    target_video_bitrate -= target_audio_bitrate
    
                    file_name_webm = f"{file_name}_{target_video_bitrate}kbps.webm"
                    ffmpegcommand_pass1 = ["ffmpeg", "-i", file_name,
                                          "-b:v", str(target_video_bitrate),
                                          "-b:a", str(target_audio_bitrate),
                                          "-pass", "1",
                                          "-f", "webm"]
                    ffmpegcommand_pass2 = ["ffmpeg", "-i", file_name,
                                          "-b:v", str(target_video_bitrate),
                                          "-b:a", str(target_audio_bitrate),
                                          "-pass", "2",
                                          file_name_webm]


#                    ffmpegcommand = ["cp", "biden.webm", file_name_webm]
                    #TODO: check return code
                    process = await asyncio.create_subprocess_exec(
                        *ffmpegcommand_pass1,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    process = await asyncio.create_subprocess_exec(
                        *ffmpegcommand_pass2,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # Wait for the process to complete and get its stdout/stderr
                    stdout, stderr = await process.communicate()
                    
                    #subprocess.run(ffmpegcommand)
                    await message.channel.send(content=f"file {file_name} has been converted to {target_video_bitrate}kbps as {file_name_webm}")
                    file_name = file_name_webm 

                # Upload file to webm archive channel
                # Also, Upload file to posted channel, since reddit does not embed videos
                await message.channel.send(file=discord.File('./' + file_name))
                await webm_archive_channel.send(file=discord.File('./' + file_name))

                # Remove webm that was downloaded
                os.remove(os.path.join("./", file_name))


bot.run(TOKEN)
