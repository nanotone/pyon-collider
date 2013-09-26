import struct


class blob(str):
	"""
	A dummy subclass of str, for OSC blobs (which are just python strings)
	"""
	pass

def pad32bit(s):
	"""
	Pad the string s with null bytes to be a multiple of 4 bytes.
	"""
	return s + ['', '\0\0\0', '\0\0', '\0'][len(s) % 4]


oscFormatters = {
	int:   (lambda x: struct.pack('!i', x)),
	float: (lambda x: struct.pack('!f', x)),
	str:   (lambda x: pad32bit(x + '\0')),
	blob:  (lambda x: struct.pack('!i', len(x)) + pad32bit(x)),
}

oscTypes = {int: 'i', float: 'f', str: 's', blob: 'b'}


def shiftStr(s):
	idx = s.find('\0')
	return s[:idx], s[idx + 4 - idx%4:]

def shiftBlob(s):
	(size, s) = oscShifters['i'](s)
	return blob(s[size:]), s[size + 3 - (size-1)%4:]


oscShifters = {
	'i': lambda s: (struct.unpack('!i', s[:4])[0], s[4:]),
	'f': lambda s: (struct.unpack('!f', s[:4])[0], s[4:]),
	's': shiftStr,
	'b': shiftBlob,
}


def pack(cmd, *args):
	args = list(args)
	for (i, x) in enumerate(args):
		if type(x) is str and '\0' in x:
			args[i] = blob(x)
	typeTag = ',' + ''.join(oscTypes[type(x)] for x in args)
	return ''.join(oscFormatters[type(x)](x) for x in [cmd, typeTag] + args)


def unpack(s):
	(cmd, s) = shiftStr(s)
	(typeTag, s) = shiftStr(s)
	result = [cmd, typeTag]
	for t in typeTag[1:]:
		(arg, s) = oscShifters[t](s)
		result.append(arg)
	return result
