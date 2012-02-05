import re
import struct
import subprocess
import sys

PORT = 57110
if len(sys.argv) > 1:
	PORT = int(sys.argv[1])

proc = subprocess.Popen('tcpdump -i lo0 -l -x'.split() + ['dst port %d' % PORT], stdout=subprocess.PIPE)

buf = ''
def read_str(s):
	i = s.index('\x00')
	j = i + 4 - (i % 4)
	return s[:i], s[j:]

def read_packet(s):
	if s.startswith('/'):
		(cmd, s) = read_str(s)
		(fmt, s) = read_str(s)
		msg = (cmd,)
		for f in fmt[1:]:
			if f in 'if':
				x = struct.unpack('!'+f, s[:4])[0]
				s = s[4:]
			elif f == 's':
				(x, s) = read_str(s)
			elif f == 'b':
				size = struct.unpack('!I', s[:4])[0]
				x = s[4:4 + x]
				s = s[4 + x + (3 - (x+3) % 4):]
			else:
				assert False, "unknown type %r" % f
			msg += (x,)
		return (msg, s)
	elif s.startswith('#bundle'):
		(x, s) = read_str(s)
		assert x == '#bundle'
		bun = [struct.unpack('!Q', s[:8])[0]]
		s = s[8:]
		while len(s) > 4:
			size = struct.unpack('!I', s[:4])[0]
			if size % 4 != 0 or 4 + size > len(s):
				break
			s = s[4:]
			(x, s) = (s[:size], s[size:])
			bun.append(read_packet(x)[0])
		return (bun, s)
	else:
		assert False

def cmd_nums_to_strs(tup):
	def convert(value):
		if type(value) is str:
			return {
				'/09': '/s_new',
				'/11': '/n_free',
				'/24': '/g_freeAll',
			}.get(value, value)
		if type(value) is tuple:
			return cmd_nums_to_strs(value)
		return value
	return tuple(map(convert, tup))

while True:
	line = proc.stdout.readline()
	if 'UDP' in line and buf:
		def repl(match):
			s = match.group(0)
			cmd = ord(s[3])
			if 0 < cmd < 63:
				return '/%02d\0,' % cmd
			return s
		buf = re.sub('\0\0\0.,', repl, buf)
		match = re.search(r'(/[a-z\d]|#bundle).+', buf)
		if not match:
			print "NO MATCH IN", repr(buf)
		else:
			osc = match.group(0)
			(x, s) = read_packet(osc)
			x = cmd_nums_to_strs(x)
			if not (type(x) is tuple and x[0] == '/status'):
				print x
		buf = ''
	else:
		line = line.split(':')[1].strip().replace(' ', '')
		for i in xrange(0, len(line), 2):
			c = chr(eval('0x' + line[i:i+2]))
			#if buf or c in '/#':
			buf += c

