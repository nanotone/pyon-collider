import Queue
import socket
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
		self.booted = False

		self.bundle_depth = 0
		self.bundle_msgs = []
		class BundledContext(object):
			def __enter__(_self):
				self.bundle_depth += 1
			def __exit__(_self, exc_type, exc_value, traceback):
				self.bundle_depth -= 1
				if self.bundle_depth == 0:
					if exc_type is None:
						self.sendBundle(*self.bundle_msgs)
					self.bundle_msgs = []
		self.bundled = BundledContext()

	def boot(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		cmd = 'cd %s; ./scsynth -u %d -R 0' % (SCSYNTH_DIR, self.port)
		self.proc = subprocess.Popen(['bash', '-c', cmd])
		self.recv_thread = threading.Thread(target=self.run_recv)
		self.recv_thread.daemon = True
		self.recv_thread.start()

		start = time.time()
		while not self.booted:
			if time.time() - start > 5:
				raise Exception("scsynth not ready after 5 seconds; aborting")
			self.send('/status')
			time.sleep(0.5)  # clunky

	def run_recv(self):
		while True:
			msg = self.sock.recv(1024)
			msg = osc.unpack(msg)
			if msg[0] == '/status.reply':
				self.booted = True
			print "Received", msg

	def quit(self):
		self.send('/quit')
		self.send = self.sendBundle = (lambda *args: None)

	def send(self, *args):
		assert None not in args, "Cannot send " + repr(args)
		if self.bundle_depth:
			self.bundle_msgs.append(args)
		else:
			self.sock.sendto(osc.pack(*args), ('127.0.0.1', self.port))
			print "Sent", args

	def sendBundle(self, *msgs):
		self.sock.sendto(osc.packBundle(*msgs), ('127.0.0.1', self.port))
		print "Sent bundle", msgs
