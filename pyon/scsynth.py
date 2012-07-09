import Queue
import socket
import StringIO
import struct
import subprocess
import sys
import threading
import time

import osc


SCSYNTH_DIR = '/Users/yang/Applications/SuperCollider'
SCSYNTH_PORT = 57117

# scsynth process control
class ScSynth(object):
	def __init__(self, port=SCSYNTH_PORT):
		self.port = port
		self.sock = None
		self.ctl = Queue.Queue(1)
		self.bundle_depth = 0
		self.bundle_msgs = []
		class BundledContext(object):
			@staticmethod
			def __enter__():
				self.bundle_depth += 1
			@staticmethod
			def __exit__(exc_type, exc_value, traceback):
				self.bundle_depth -= 1
				if self.bundle_depth == 0:
					if exc_type is None:
						self.sendBundle(*self.bundle_msgs)
					self.bundle_msgs = []
		self.bundled = BundledContext

	def boot(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.connect(('127.0.0.1', self.port))
		cmd = 'cd %s; ./scsynth -u %d -R 0' % (SCSYNTH_DIR, self.port)
		self.proc = subprocess.Popen(['bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT) 
		self.thread = threading.Thread(target=self.run)
		self.thread.start()
		assert self.ctl.get() == 'boot'

	def run(self):
		while True:
			line = self.proc.stdout.readline()
			if not line: break
			sys.stdout.write(line)
			if line.startswith('SuperCollider 3 server ready..'):
				self.ctl.put('boot')
		self.ctl.put('quit')

	def quit(self):
		self.send('/quit')
		self.send = self.sendBundle = (lambda *args: None)
		assert self.ctl.get() == 'quit'

	def send(self, *args):
		assert None not in args, "Cannot send " + repr(args)
		if self.bundle_depth:
			self.bundle_msgs.append(args)
		else:
			self.sock.send(osc.pack(*args))
		print "Sent", repr(args)

	def sendBundle(self, *msgs):
		s = StringIO.StringIO()
		s.write('#bundle\0\0\0\0\0\0\0\0\1')
		for msg in msgs:
			msg = osc.pack(*msg)
			s.write(struct.pack('!I', len(msg)))
			s.write(msg)
		self.sock.send(s.getvalue())
		print "Sent %s" % repr((1, msgs))
