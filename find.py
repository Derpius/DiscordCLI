def mention(name: str, members: list) -> str:
	matches = []
	for member in members:
		idx = -1

		# Match nickname
		if member.nick:
			idx = member.nick.find(name)
			if idx < 0:
				idx = member.nick.lower().find(name.lower()) * 2

		# If no match, match username
		if idx < 0:
			idx = member.name.find(name) * 3
		if idx < 0:
			idx = member.name.lower().find(name.lower()) * 4

		# If match, append to matches
		if idx >= 0:
			matches.append((idx, member.mention))

	if len(matches) > 0:
		def sorter(v):
			return v[0]
		matches.sort(key=sorter)
		return matches[0][1]
	else:
		return "@" + name

def emote(name: str, emotes: list) -> str:
	matches = []
	for emote in emotes:
		# Match upper then lowercase
		idx = emote.name.find(name)
		if idx == -1:
			idx = emote.name.lower().find(name.lower())

		# If match, append to matches
		if idx != -1:
			matches.append((idx, str(emote)))

	if len(matches) > 0:
		def sorter(v):
			return v[0]
		matches.sort(key=sorter)
		return matches[0][1]
	else:
		return ":" + name + ":"

def channel(name: str, channels: list) -> str:
	matches = []
	for channel in channels:
		# Match upper then lowercase
		idx = channel.name.find(name)
		if idx == -1:
			idx = channel.name.lower().find(name.lower())

		# If match, append to matches
		if idx != -1:
			matches.append((idx, channel.mention))

	if len(matches) > 0:
		def sorter(v):
			return v[0]
		matches.sort(key=sorter)
		return matches[0][1]
	else:
		return ":" + name + ":"
