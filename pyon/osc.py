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
	return s + '\0' * [0, 3, 2, 1][len(s) % 4]


oscFormatters = {
	int:   (lambda x: struct.pack('!i', x)),
	float: (lambda x: struct.pack('!f', x)),
	str:   (lambda x: pad32bit(x + '\0')),
	blob:  (lambda x: struct.pack('!i', len(x)) + pad32bit(x)),
}

oscTypes = {int: 'i', float: 'f', str: 's', blob: 'b'}


def pack(cmd, *args):
	args = list(args)
	for (i, x) in enumerate(args):
		if type(x) is str and '\0' in x:
			args[i] = blob(x)
	typeTag = ',' + ''.join(oscTypes[type(x)] for x in args)
	return ''.join(oscFormatters[type(x)](x) for x in [cmd, typeTag] + args)
