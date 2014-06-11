import time

from pyon import pool, scengine
import synthdefs


class DecayEnv(object):
	def __init__(self):
		self.o = self.decay = engine.synth('decay', i=engine.kb0)
	def trigger(self):
		thing = self.decay.i
		with engine.bundle:
			self.decay.i = engine.synth('delta', freq=0)

class Instr(object):
	def __init__(self):
		import collections
		self.voices = collections.deque()
	def play(self, pitch):
		now = time.time()
		with engine.bundle:
			if not self.voices or now < self.voices[0]['time'] + 1.1:
				#print "creating a new voice"
				decay = DecayEnv()
				s = engine.synth('sine', amp=decay, freq=pitch)
				voice = {'decay': decay, 's': s}
			else:
				voice = self.voices.popleft()
				voice['s'].freq = pitch
			voice['time'] = now
			voice['decay'].trigger()
			self.voices.append(voice)

def main():
	#amp = Synth('ksin', freq=1, o=bus._id)
	instr = Instr()
	for x in range(100):
		instr.play([440, 660, 880][x % 3])
		time.sleep(0.2)

if __name__ == '__main__':
	engine = scengine.ScEngine()
	for sd in synthdefs.gen_synthdefs():
		engine.send_synthdef(sd)
	#engine.send('/dumpOSC', 1); time.sleep(0.1)
	try:
		main()
	finally:
		engine.shutdown()
