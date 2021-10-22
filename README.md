# DiscordCLI
Command line interface for controlling a Discord bot

Features:
* Easy to extend command system
* Simple channel and guild switching
* Mention, emote, and channel resolution
* Mention notifications

Try it [here](https://replit.com/@Derpius/DiscordCLI)

**Due to using urwid this is not compatible with Windows**

# How to use
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and make an app with any name you like.
2. Under the bot tab, create a bot and name it whatever you like (this is your display name).
3. You **must** turn on `Server Member Intent` and `Presence Intent` for the client to work.
4. In the `OAuth2` tab, tick the `bot` checkbox and set the permissions to the following in the panel below:  
![Permissions](https://i.imgur.com/x1ggqFE.png)  
5. Navigate to the link above the bot permissions box and invite the bot to the discord server(s) you want it to be in.  
*you must have manage server permissions to invite the bot*
6. Go back to the bot tab and copy the token for use with DiscordCLI.
7. Optionally add the token (and other settings) as environment variables to save configuring every time you run.
