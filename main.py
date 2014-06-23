import time

from pyon import pool, scengine
import synthdefs


class DecayEnv(object):
	def __init__(self, amp=1):
		self.out = self.decay = engine.synth('decay2')
		self.amp = amp
	def trigger(self):
		with engine.bundle:
			self.decay.i = engine.synth('delta', freq=0, amp=self.amp)

class Instr(object):
	def __init__(self):
		import collections
		self.voices = collections.deque()
	def play(self, pitch, amp=1):
		now = time.time()
		with engine.bundle:
			if not self.voices or now < self.voices[0]['time'] + 1.1:
				#print "creating a new voice"
				decay = DecayEnv(amp)
				s = engine.synth('sin', amp=decay, freq=pitch)
				voice = {'decay': decay, 's': s}
			else:
				voice = self.voices.popleft()
				voice['s'].freq = pitch
			voice['time'] = now
			voice['decay'].trigger()
			self.voices.append(voice)

m2 = 2 ** (1/12.0)

class Instr2(object):
	def __init__(self):
		self.s = None
	def play(self, pitch):
		with engine.bundle:
			if self.s:
				self.s.free()
			if pitch:
				self.s = engine.synth('sin', amp=-15, freq=220 * m2**4)
			else:
				self.s = None

def main():
	#amp = Synth('ksin', freq=1, out=bus._id)
	instr = Instr()
	instr2 = Instr2()
	instr2.play(110 * m2**4)
	for x in range(15):
		with engine.bundle:
			if x % 2 == 0:
				note = engine.synthdefs['kick']()
			instr.play([440, 660, 880][x % 3], amp=-20)
		time.sleep(0.25)
	time.sleep(3)

if __name__ == '__main__':
	engine = scengine.ScEngine()
	for sd in synthdefs.gen_synthdefs():
		engine.send_synthdef(sd)
	print "Waiting for synthdefs to be loaded"
	while engine.sc.pending_recvs:
		time.sleep(0.1)
	#engine.send('/dumpOSC', 1); time.sleep(0.1)
	try:
		main()
	finally:
		engine.shutdown()
