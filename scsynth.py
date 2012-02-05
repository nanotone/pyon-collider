import socket
import StringIO
import struct
import subprocess
import sys
import threading

SCSYNTH_DIR = '/Users/yang/Applications/SuperCollider'

class blob(str): pass

pad32bit = lambda x: x + '\x00' * [0, 3, 2, 1][len(x) % 4]

oscFormatters = {
	int:   (lambda x: struct.pack('!i', x)),
	float: (lambda x: struct.pack('!f', x)),
	str:   (lambda x: pad32bit(x + '\x00')),
	blob:  (lambda x: struct.pack('!i', len(x)) + pad32bit(x)),
}

oscTypes = {int: 'i', float: 'f', str: 's', blob: 'b'}

def oscformat(*args):
	return ''.join(oscFormatters[type(data)](data) for data in args)

def oscpack(cmd, *args):
	typeTag = ',' + ''.join(oscTypes[type(x)] for x in args)
	return oscformat(cmd, typeTag, *args)

sock = None

def boot(port):
	global sock
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.connect(("127.0.0.1", port))
	global server
	cmd = 'cd %s; ./scsynth -u %d -R 0' % (SCSYNTH_DIR, port)
	server = subprocess.Popen(['bash','-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	def run():
		while True:
			line = server.stdout.readline()
			if not line: break
			sys.stdout.write(line)
		print "scsynth exited"
	thread = threading.Thread(target=run)
	thread.start()

def send(*args):
	sock.send(oscpack(*args))
	print "Sent", repr(args)

def sendBundle(*msgs):
	s = StringIO.StringIO()
	s.write('#bundle\0\0\0\0\0\0\0\0\1')
	for msg in msgs:
		msg = oscpack(*msg)
		s.write(struct.pack('!I', len(msg)))
		s.write(msg)
	sock.send(s.getvalue())
	print "Sent %s" % repr((1, msgs))

def quit():
	send('/quit')
