import Queue
import socket
import StringIO
import struct
import subprocess
import sys
import threading
import time

SCSYNTH_DIR = '/Users/yang/Applications/SuperCollider'
SCSYNTH_PORT = 57117


# OSC

class blob(str): pass

pad32bit = lambda x: x + '\0' * [0, 3, 2, 1][len(x) % 4]

oscFormatters = {
	int:   (lambda x: struct.pack('!i', x)),
	float: (lambda x: struct.pack('!f', x)),
	str:   (lambda x: pad32bit(x + '\0')),
	blob:  (lambda x: struct.pack('!i', len(x)) + pad32bit(x)),
}

oscTypes = {int: 'i', float: 'f', str: 's', blob: 'b'}

def oscpack(cmd, *args):
	args = list(args)
	for (i, x) in enumerate(args):
		if type(x) is str and '\0' in x:
			args[i] = blob(x)
	typeTag = ',' + ''.join(oscTypes[type(x)] for x in args)
	return ''.join(oscFormatters[type(x)](x) for x in [cmd, typeTag] + args)


# scsynth process control

sock = None
ctrl = Queue.Queue(1)

def boot(port=SCSYNTH_PORT):
	global sock
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.connect(("127.0.0.1", port))
	global server
	cmd = 'cd %s; ./scsynth -u %d -R 0' % (SCSYNTH_DIR, port)
	server = subprocess.Popen(['bash','-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
	thread = threading.Thread(target=runServer)
	thread.start()
	assert ctrl.get() == 'boot'

def runServer():
	while True:
		line = server.stdout.readline()
		if not line: break
		sys.stdout.write(line)
		if line.startswith('SuperCollider 3 server ready..'):
			ctrl.put('boot')
	ctrl.put('quit')

def quit():
	send('/quit')
	global send, sendBundle
	send = sendBundle = (lambda *args: None)
	assert ctrl.get() == 'quit'


# messages and bundles

def send(*args):
	assert None not in args, "Cannot send " + repr(args)
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


class BundleContext(object):

	def __init__(self):
		self.depth = 0
		self.msgs = []

	def __enter__(self):
		self.depth += 1

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.depth -= 1
		if self.depth == 0:
			if not exc_type:
				sendBundle(*self.msgs)
			self.msgs = []

