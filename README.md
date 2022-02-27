# Shiver Me Timbers Bot
- A discord bot that will monitor for a link to a 4chan webm, go to the link, download it, and reupload to the server in which it was posted in order to preserve the content
- Once added to the server, the bot will monitor each text channel and continually check to see if the last message posted was a link to a webm on 4Chan
- Links to 4Chan are broken once threads are archived, so this bot intends to preserve the content by uploading the file directly to the server
- The bot checks to see if there is a channel called "webm-archive" and if there isn't, it creates one and uploads webms there
- The bot is added with administrator privledges to the server in order to create a text channel and monitor messages
