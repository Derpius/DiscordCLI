import os
import asyncio
from typing import Union
from inspect import signature

import discord
import urwid

import time
import pytz
import datetime

from terminal import Terminal
import find

# Get initial config
TOKEN = os.environ["TOKEN"] if "TOKEN" in os.environ else input("Enter a Discord bot token: ")
TIMEZONE = os.environ["TIMEZONE"] if "TIMEZONE" in os.environ else input("Enter your timezone code (defaults to UTC): ")
TYPING_CUTOFF = 10

try:
	TIMEZONE = pytz.timezone(TIMEZONE)
except pytz.exceptions.UnknownTimeZoneError:
	TIMEZONE = pytz.utc

intents = discord.Intents().default()
intents.members = True
intents.typing = True
intents.presences = True
client = discord.Client(intents=intents)

current_channel = 0
current_guild = 0
client_ready = False

client_typing = False
client_typing_when = None

unread_channels = set()

typing = {}

commands = {}

terminal = Terminal()

def print_message(message: discord.Message):
	name = "ERROR"
	try:
		name = message.author.nick if message.author.nick else message.author.name
	except AttributeError:
		name = message.author.name

	msg_time = message.created_at.replace(tzinfo=pytz.utc).astimezone(TIMEZONE).strftime('%H:%M')

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
	if message.author.id in typing:
		del typing[message.author.id]
		draw_typing()

	if message.channel.id == current_channel:
		print_message(message)
	elif message.guild:
		unread_channels.add(message.channel.id)
		if client.user.mentioned_in(message):
			terminal.print(
				f"You just got mentioned at {message.guild.name if message.guild else 'Nowhere'} in {message.channel.category if message.channel.category else 'no-category'}:{message.channel.name}"
			)

def draw_typing():
	valid_typers = [typer[1] for k, typer in typing.items() if typer[0].id == current_channel]
	len_typing = len(valid_typers)

	text = ""
	if len_typing == 1:
		typer = valid_typers[0]
		text = f"{typer.nick if typer.nick else typer.name} is typing..."
	elif len_typing == 2:
		typera, typerb = valid_typers[0], valid_typers[1]
		text = f"{typera.nick if typera.nick else typera.name} and {typerb.nick if typerb.nick else typerb.name} are typing..."
	elif len_typing > 5:
		text = "Several people are typing..."
	else:
		for i in range(len_typing):
			typer = valid_typers[i]
			if i < len_typing - 1:
				text += (typer.nick if typer.nick else typer.name) + ", "
			else:
				text += f"and {typer.nick if typer.nick else typer.name} are typing..."
	terminal.set_status(text)

@client.event
async def on_typing(
	channel: discord.abc.Messageable,
	user: Union[discord.User, discord.Member],
	when: datetime.datetime
):
	if not client_ready: return
	if user.id == client.user.id: return
	typing[user.id] = (channel, user, when)
	if channel.id == current_channel: draw_typing()

async def invalidate_typing():
	while True:
		dirty = False
		keys = list(typing)
		for key in keys:
			if (datetime.datetime.now() - typing[key][2]).total_seconds() > TYPING_CUTOFF:
				del typing[key]
				dirty = True
		if dirty: draw_typing()

		await asyncio.sleep(0.1)

async def handle_client_typing():
	global client_typing
	while True:
		while not client_typing or time.time() - client_typing_when > TYPING_CUTOFF:
			await asyncio.sleep(0.1)
		async with client.get_channel(current_channel).typing():
			while client_typing and time.time() - client_typing_when < TYPING_CUTOFF:
				await asyncio.sleep(0.01)
			client_typing = False

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
						member = find.member(args[i][1:], guild.members)
						if member: args[i] = member.mention
					elif len(args[i]) > 2 and args[i][0] == ":" and args[i][-1] == ":":
						emote = find.emote(args[i][1:-1], guild.emojis)
						if emote: args[i] = str(emote)
					elif len(args[i]) > 1 and args[i][0] == "#":
						channel = find.channel(args[i][1:], guild.text_channels)
						if channel: args[i] = channel.mention
				inp = " ".join(args)

				channel = client.get_channel(current_channel)
				if channel.permissions_for(channel.guild.me).send_messages:
					await channel.send(inp)
				else:
					terminal.print("You do not have permission to send messages in this channel")

		await asyncio.sleep(0.01)

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
			func.__doc__ if func.__doc__ else "No description"
		)
	else:
		commands[func.__name__] = (
			lambda *args: func(*(args[:len(sig.parameters)])),
			str(sig)[1:-1],
			func.__doc__ if func.__doc__ else "No description"
		)

# Terminal Commands

@command
async def channel(channel_name, category_name = None):
	'''Switches to a channel'''
	if not channel_name:
		terminal.print("Missing required parameter channel_name")
		return

	match = find.channel(
		channel_name,
		client.get_guild(current_guild).channels,
		category_name
	)

	if not match:
		if category_name:
			terminal.print(f"Couldn't find channel '{category_name}:{channel_name}'")
		else:
			terminal.print(f"Couldn't find channel '{channel_name}'")
		return
	
	if not match.permissions_for(match.guild.me).view_channel:
		terminal.print("You do not have permission to view this channel")
		return

	global current_channel, client_ready
	client_ready = False
	current_channel = match.id

	if match.permissions_for(match.guild.me).read_message_history:
		history = await match.history(limit=128).flatten()
		for i in range(len(history) - 1, -1, -1):
			print_message(history[i])

	if match in unread_channels:
		unread_channels.remove(match)

	global typing, client_typing
	client_typing = False
	typing = {}
	draw_typing()

	if match.category:
		terminal.print(f"Successfully switched to channel '{match.category.name}:{match.name}'")
		terminal.set_prompt(
			f"{match.category.name}:{match.name}> "
		)
	else:
		terminal.print(f"Successfully switched to channel '{match.name}'")
		terminal.set_prompt(
			f"{match.name}> "
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
		return

	guilds = client.guilds
	match = find.guild(guild_name, guilds)

	if not match:
		terminal.print(f"Couldn't find guild '{guild_name}'")
	else:
		global current_channel, current_guild, client_ready
		client_ready = False
		current_guild = match.id

		if len(match.text_channels) < 1:
			raise Exception("Guild has no text channels")

		channel = None
		if (
			match.system_channel and
			match.system_channel.permissions_for(match.me).view_channel
		):
			channel = match.system_channel
		else:
			for possible_channel in match.text_channels:
				if possible_channel.permissions_for(possible_channel.guild.me).view_channel:
					channel = possible_channel
					break
		if not channel: raise Exception("Guild has no public text channels")
		current_channel = channel.id

		if channel.permissions_for(channel.guild.me).read_message_history:
			history = await channel.history(limit=128).flatten()
			for i in range(len(history) - 1, -1, -1):
				print_message(history[i])

		global typing, client_typing
		client_typing = False
		typing = {}
		draw_typing()

		terminal.print(f"Successfully switched to guild '{match.name}'")
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

@command
async def emotes():
	'''Prints a list of emotes on the server'''
	terminal.print("Emotes:")
	for emote in client.get_guild(current_guild).emojis:
		terminal.print(f":{emote.name}: - {str(emote.url)}")

@command
async def online():
	'''Prints a list of the online users in this guild'''
	terminal.print("Online:")
	for member in client.get_guild(current_guild).members:
		if member.status is discord.Status.online:
			if member.nick:
				terminal.print(f"{member.nick} ({member.name})")
			else:
				terminal.print(member.name)

@command
async def status(username):
	'''Get status information for a user'''
	user = find.member(username, client.get_guild(current_guild).members)
	if not user:
		terminal.print(f"Couldn't find user '{username}'")
		return

	terminal.print(f"Current status for {user.name}:")
	if user.nick: terminal.print("Guild Nickname: " + user.nick)
	terminal.print("Status: " + user.raw_status)
	terminal.print("Activity: " + (user.activity.name if user.activity else "Nothing"))

# Terminal colour scheme
palette = [
	("primary", "white", "black"),
	("secondary", "light gray", "dark cyan")
]

# Set up event loop
client.loop.create_task(get_console())
client.loop.create_task(invalidate_typing())
client.loop.create_task(handle_client_typing())

aloop = asyncio.get_event_loop()
event_loop = urwid.AsyncioEventLoop(loop=aloop)
loop = urwid.MainLoop(terminal, palette, event_loop=event_loop)

aloop.create_task(client.start(TOKEN))

def on_user_type(key: str):
	if len(terminal.chatbox.edit_text) > 0:
		if terminal.chatbox.edit_text[0] == "/": return
	elif key == "/": return

	channel = client.get_channel(current_channel)
	if channel.permissions_for(channel.guild.me).send_messages:
		global client_typing, client_typing_when
		client_typing = True
		client_typing_when = time.time()
terminal.typing_callback = on_user_type

loop.run()
