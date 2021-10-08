import discord
import asyncio
import urwid
from terminal import Terminal
from inspect import signature
import find

import os

# Get initial config
TOKEN = os.environ["TOKEN"] if "TOKEN" in os.environ else input("Enter a Discord bot token: ")
TIMEZONE = os.environ["TIMEZONE"] if "TIMEZONE" in os.environ else input("Enter your timezone code (defaults to UTC): ")


intents = discord.Intents().default()
intents.members = True
client = discord.Client(intents=intents)

current_channel = 0
current_guild = 0
client_ready = False

unread_channels = set()

commands = {}

terminal = Terminal()



def print_message(message: discord.Message):
	name = "ERROR"
	try:
		name = message.author.nick if message.author.nick else message.author.name
	except AttributeError:
		name = message.author.name

	msg_time = message.created_at.strftime('%H:%M')

	if len(message.clean_content) > 0:
		terminal.print(f"{msg_time} {name}: {message.clean_content}")
	for attachment in message.attachments:
		terminal.print(f"{msg_time} {name}: {attachment.url}")

	for embed in message.embeds:
		if (
			embed.author == discord.Embed.Empty or
			embed.description == discord.Embed.Empty
		): continue

		terminal.print(f"{name}: --EMBED: {embed.author.name}--")
		terminal.print(embed.description)

# Initialisation
@client.event
async def on_ready():
	if len(client.guilds) < 1: raise Exception("Bot isn't a member of any guilds")

	valid_channel = None
	for guild in client.guilds:
		if len(guild.text_channels) > 0:
			valid_channel = guild.text_channels[0]
	if not valid_channel: raise Exception("Couldn't find a text channel in any guilds")

	global current_channel, current_guild
	current_channel = valid_channel.id
	current_guild = valid_channel.guild.id

	terminal.set_title(f"{valid_channel.guild.name} - {client.user.name}")

	channel = client.get_channel(current_channel)
	terminal.set_prompt(
		f"{channel.category.name if channel.category else 'no-category'}:{channel.name}> "
	)

	history = await channel.history(limit=128).flatten()
	for i in range(len(history) - 1, -1, -1):
		print_message(history[i])

	global client_ready
	client_ready = True

# Print messages from the channel we're in
@client.event
async def on_message(message: discord.Message):
	if not client_ready: return

	if message.channel.id == current_channel:
		print_message(message)
	elif message.guild:
		unread_channels.add(message.channel.id)
		if client.user.mentioned_in(message):
			terminal.print(
				f"You just got mentioned at {message.guild.name if message.guild else 'Nowhere'} in {message.channel.category if message.channel.category else 'no-category'}:{message.channel.name}"
			)

async def command_handler(command, *args):
	if command == "help":
		terminal.print("Commands:")
		for command_name, command_obj in commands.items():
			terminal.print(f"/{command_name} {command_obj[1]}\n- {command_obj[2]}")
	elif command in commands:
		await commands[command][0](*args)
	else:
		terminal.print(f"Unkown command '{command}'")

async def get_console():
	while True:
		if client_ready:
			inp = await terminal.input()
			args = inp.split(" ")

			if len(inp) >= 2 and inp[0] == "/":
				args[0] = args[0][1:]
				await command_handler(*args)
			elif len(inp) > 0:
				guild = client.get_guild(current_guild)

				# Resolve mentions
				for i in range(len(args)):
					if len(args[i]) > 1 and args[i][0] == "@":
						args[i] = find.mention(args[i][1:], guild.members)
					elif len(args[i]) > 2 and args[i][0] == ":" and args[i][-1] == ":":
						args[i] = find.emote(args[i][1:-1], guild.emojis)
					elif len(args[i]) > 1 and args[i][0] == "#":
						args[i] = find.channel(args[i][1:], guild.text_channels)
				inp = " ".join(args)

				channel = client.get_channel(current_channel)
				if channel.permissions_for(channel.guild.me).send_messages:
					await channel.send(inp)
				else:
					terminal.print("You do not have permission to send messages in this channel")

		await asyncio.sleep(0.1)

def command(func):
	sig = signature(func)
	vararg = False
	for param in sig.parameters.values():
		if param.kind == param.VAR_POSITIONAL:
			vararg = True
			break

	if vararg:
		commands[func.__name__] = (
			lambda *args: func(*args),
			str(sig)[1:-1],
			func.__doc__ if func.__doc__ else "No documentation"
		)
	else:
		commands[func.__name__] = (
			lambda *args: func(*(args[:len(sig.parameters)])),
			str(sig)[1:-1],
			func.__doc__ if func.__doc__ else "No documentation"
		)

# Terminal Commands
@command
async def channel(channel_name, category_name = None):
	'''Switches to a channel'''
	if not channel_name:
		terminal.print("Missing required parameter channel_name")

	channels = client.get_guild(current_guild).channels
	matches = [
		(
			channel.id,
			channel.name,
			channel.category.name if channel.category is not None else "no-category",
			channel
		)
		for channel in channels
		if channel_name == channel.name
	]

	if category_name:
		matches = [match for match in matches if match[2].lower() == category_name.lower()]

	if len(matches) == 0:
		terminal.print(f"Couldn't find channel '{channel_name}'")
	else:
		if not matches[0][3].permissions_for(matches[0][3].guild.me).view_channel:
			terminal.print("You do not have permission to view this channel")
			return

		global current_channel, client_ready
		client_ready = False
		current_channel = matches[0][0]

		if matches[0][3].permissions_for(matches[0][3].guild.me).read_message_history:
			history = await matches[0][3].history(limit=128).flatten()
			for i in range(len(history) - 1, -1, -1):
				print_message(history[i])

		if matches[0][0] in unread_channels:
			unread_channels.remove(matches[0][0])

		terminal.print(f"Successfully switched to channel '{matches[0][1]}'")
		terminal.set_prompt(
			f"{matches[0][2]}:{matches[0][1]}> "
		)

		client_ready = True

@command
async def channels():
	'''Prints a list of all channels'''
	channels = client.get_guild(current_guild).text_channels
	tree = {}
	for channel in channels:
		if not channel.permissions_for(channel.guild.me).view_channel:
			continue

		category = channel.category.name if channel.category else "no-category"
		if category not in tree: tree[category] = []
		tree[category].append((channel.name, channel.id in unread_channels))
	
	terminal.print("Channels:")
	for category, channel_names in tree.items():
		terminal.print(category)
		for channel in channel_names:
			terminal.print("    " + channel[0] + (" *" if channel[1] else ""))

@command
async def guild(*args):
	'''Switches to a guild'''
	guild_name = " ".join(args)
	if len(guild_name) == 0:
		terminal.print("Missing required parameter guild_name")
	
	guilds = client.guilds
	matches = [
		(guild.id, guild.name, guild)
		for guild in guilds
		if guild_name == guild.name
	]

	if len(matches) == 0:
		terminal.print(f"Couldn't find guild '{guild_name}'")
	else:
		global current_channel, current_guild, client_ready
		client_ready = False
		current_guild = matches[0][0]

		if len(matches[0][2].text_channels) < 1:
			raise Exception("Guild has no text channels")

		channel = None
		if (
			matches[0][2].system_channel and
			matches[0][2].system_channel.permissions_for(matches[0][2].me).view_channel
		):
			channel = matches[0][2].system_channel
		else:
			for possible_channel in matches[0][2].text_channels:
				if possible_channel.permissions_for(possible_channel.guild.me).view_channel:
					channel = possible_channel
					break
		if not channel: raise Exception("Guild has no public text channels")
		current_channel = channel.id

		global members, emotes
		members = matches[0][2].members
		emotes = matches[0][2].emojis

		if channel.permissions_for(channel.guild.me).read_message_history:
			history = await channel.history(limit=128).flatten()
			for i in range(len(history) - 1, -1, -1):
				print_message(history[i])

		terminal.print(f"Successfully switched to guild '{matches[0][1]}'")
		terminal.set_prompt(
			f"{channel.category.name if channel.category else 'no-category'}:{channel.name}> "
		)

		client_ready = True

@command
async def guilds():
	'''Prints a list of all guilds this bot is in'''
	terminal.print("Guilds:")
	for guild in client.guilds:
		terminal.print(guild.name)

@command
async def nick(*args):
	'''Changes the bot's nickname'''
	new_name = " ".join(args)
	if not new_name or len(new_name) == 0: new_name = client.user.name
	member = client.get_guild(current_guild).get_member(client.user.id)
	await member.edit(nick=new_name)

# Set up event loop
client.loop.create_task(get_console())

aloop = asyncio.get_event_loop()
event_loop = urwid.AsyncioEventLoop(loop=aloop)
loop = urwid.MainLoop(terminal, event_loop=event_loop)

aloop.create_task(client.start(TOKEN))

def on_user_type():
	if terminal.chatbox.edit_text[0] == "/": return
	channel = client.get_channel(current_channel)
	if channel.permissions_for(channel.guild.me).send_messages:
		asyncio.ensure_future(channel.trigger_typing(), loop=aloop)
terminal.typing_callback = on_user_type

loop.run()
