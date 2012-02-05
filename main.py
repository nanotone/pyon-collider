import collections
import gc
import itertools
import pprint
import sys
import time

import pool
import synthdef
import scsynth


bundle = scsynth.BundleContext()
def send(*args):
	if bundle.depth:
		bundle.msgs.append(args)
	else:
		scsynth.send(*args)
def sendBundledMsg(*args):
	with bundle:
		send(*args)


synthSpec = {
	'decay': 1,
	'delta': 1,
	'sine': 2,
}

def make_oscil(name, ugen, rate=2):
	send('/d_recv', synthdef.filewrap(synthdef.oscil(name, ugen, rate)))
#make_oscil('sin', 'SinOsc')
#make_oscil('saw', 'Saw')
#make_oscil('ksin', 'SinOsc', 1)
#make_oscil('delta', 'Impulse', rate=1)

nodePool = pool.Pool()
kbusPool = pool.Pool(0)


class Group(object):
	def __init__(self):
		self._id = nodePool.get()
		send('/g_new', self._id, 0, 0)

class KBus(object):
	def __init__(self, value=None):
		self._id = kbusPool.get()
		if value is not None:
			self.set(value)
	def set(self, value):
		sendBundledMsg('/c_set', self._id, value)
	def __del__(self):
		kbusPool.put(self._id)


class Synth(object):
	def __init__(self, synthdef, parent=None, **kwargs):
		if not parent: parent = default
		self._id = nodePool.get()
		if synthSpec.get(synthdef) == 1: # control bus out
			self._obus = KBus()
			if 'o' not in kwargs:
				kwargs['o'] = self._obus
		with bundle:
			snew = ['/s_new', synthdef, self._id, 0, parent._id]
			mapping = {}
			for (name, value) in kwargs.iteritems():
				object.__setattr__(self, name, value)
				setter = self._set(name, value)
				if setter:
					if setter[0] == 'set':
						snew.extend((name, setter[1]))
					elif setter[0] == 'map':
						mapping[name] = setter[1]
			send(*snew)
			if mapping:
				send('/n_map', self._id, *itertools.chain( *mapping.items() ))

	def __setattr__(self, name, value):
		object.__setattr__(self, name, value)
		setter = self._set(name, value)
		if setter:
			if setter[0] == 'set':
				send('/n_set', self._id, name, setter[1])
			elif setter[0] == 'map':
				sendBundledMsg('/n_map', self._id, name, setter[1])

	def _set(self, name, value):
		if name.startswith('_'):
			return
		if type(value) in (int, float):
			return ('set', value)
		elif name == 'o' and isinstance(value, KBus):
			return ('set', value._id)
		else:
			while hasattr(value, 'o'): value = value.o
			assert isinstance(value, KBus)
			return ('map', value._id)

	def __del__(self):
		send('/n_free', self._id)
		nodePool.put(self._id)


class DecayEnv(object):
	def __init__(self):
		self.o = self.decay = Synth('decay', i=kbus0)
	def trigger(self):
		thing = self.decay.i
		with bundle:
			self.decay.i = Synth('delta', freq=0)



class Instr(object):
	def __init__(self):
		self.voices = collections.deque()
	def play(self, pitch):
		now = time.time()
		with bundle:
			if not self.voices or now < self.voices[0]['time'] + 1.5:
				#print "creating a new voice"
				decay = DecayEnv()
				s = Synth('sine', amp=decay, freq=pitch)
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
	scsynth.boot()
	#send('/dumpOSC', 1); time.sleep(0.1)
	default = Group(); time.sleep(0.1)
	kbus0 = KBus()
	try:
		main()
	finally:
		scsynth.quit()

