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
**Go to the [Discord Developer Portal](https://discord.com/developers/applications) and make an app with any name you like.**

Then do the following steps:

 1. Under the bot tab, create a bot and name it what you like. The name here is what will show up in discord servers.

 2. You **MUST** turn on *Server Member Intent* & *Presence Intent* for everything to function properly.

 3. In the *OAuth2* tab tick the *bot* checkbox and a new set of permissions will appear. [Enable the following permissions:](https://imgur.com/a/Wh4414y)![Permissions](https://i.imgur.com/x1ggqFE.png)
 4. Copy the link above the bot permissions box and invite the bot to the discord server(s) you want it to be in.
      
      `note: you must have the proper permissions in the server you want to invite the bot into, otherwise it will not show up when you `

 5. Go back to the bot tab, and copy the bot token and paste it into the bot when it prompts you or make a secret called "TOKEN"

 6. Profit.
