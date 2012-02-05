import sys
import time

import pool
import synthdef
import scsynth
from scsynth import blob, boot, send, sendBundle, quit

SCSYNTH_PORT = 57117

boot(SCSYNTH_PORT)

time.sleep(1)
#send('/dumpOSC', 1)

synthSpec = {
	'decay': 1,
	'delta': 1,
	'sine': 2,
}

def make_oscil(name, ugen, rate=2):
	send('/d_recv', blob(synthdef.filewrap(synthdef.oscil(name, ugen, rate))))
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
default = Group()
time.sleep(0.5)


class KBus(object):
	def __init__(self, value=None):
		self._id = kbusPool.get()
		if value is not None:
			self.set(value)
	def set(self, value):
		sendBundle(('/c_set', self._id, value))
	def __del__(self):
		kbusPool.put(self._id)
kbus0 = KBus()


class Synth(object):
	def __init__(self, synthdef, parent=default, **kwargs):
		self._id = nodePool.get()
		if synthSpec.get(synthdef) == 1: # control bus out
			self._obus = KBus()
			if 'o' not in kwargs:
				kwargs['o'] = self._obus

		snew = ['/s_new', synthdef, self._id, 0, parent._id]
		msgs = [snew]
		if kwargs:
			for (name, value) in kwargs.iteritems():
				object.__setattr__(self, name, value)
				setter = self._set(name, value)
				if setter:
					if setter[0] == 'set':
						snew.extend((name, setter[1]))
					elif setter[0] == 'map':
						msgs.append(['/n_mapn', self._id, name, setter[1], 1])
		else:
			snew.append(0) # not sure why, but sclang does this
		if len(msgs) == 1:
			send(*snew)
		else:
			sendBundle(*msgs)

	def __setattr__(self, name, value):
		object.__setattr__(self, name, value)
		setter = self._set(name, value)
		if setter:
			if setter[0] == 'set':
				send('/n_set', self._id, name, setter[1])
			elif setter[0] == 'map':
				sendBundle(('/n_mapn', self._id, name, setter[1], 1))

	def _set(self, name, value):
		if name.startswith('_'):
			return
		if type(value) in (int, float):
			return ('set', value)
		elif name == 'o' and isinstance(value, KBus):
			return ('set', value._id)
		else:
			while hasattr(value, 'o'): value = value.o
			assert isinstance(value, KBus):
			return ('map', value._id)

	def free(self):
		send('/n_free', self._id)


class DecayEnv(object):
	def __init__(self):
		self.o = self.decay = Synth('decay', i=kbus0)

	def trigger(self):
		self.decay.i = Synth('delta', freq=0)

#bus = KBus(0)
#amp = Synth('ksin', freq=1, o=bus._id)

decay = DecayEnv()
s = Synth('sine', amp=decay)

for x in range(1,100):
	decay.trigger()
	time.sleep(x)

time.sleep(100)

quit()
sys.exit()

s.free()

time.sleep(0.5)

quit()

