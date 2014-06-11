import itertools
import time

from pyon import pool, scsynth
import synthdefs

output_rates = {}

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
	def __init__(self, synthdefName, parent=None, **kwargs):
		if not parent: parent = default
		self._id = nodePool.get()
		if output_rates.get(synthdefName) == 1: # control bus output
			self._obus = KBus()
			if 'o' not in kwargs:
				kwargs['o'] = self._obus
		with bundle:
			# setattr ALL the kwargs! But combine the sets and maps for efficiency
			snew = ['/s_new', synthdefName, self._id, 0, parent._id]
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
		"""
		Determine how to handle a setattr. Internal names are noops, scalars
		scalars (including output busses) will be n_set, and everything else
		results in an n_map.
		"""
		if name.startswith('_'):
			return
		if type(value) in (int, float):
			return ('set', value)
		elif name == 'o' and isinstance(value, KBus):
			return ('set', value._id)
		else:
			# Assume we want to n_map a kr-param to a kr-synth's output
			# This is a bit tricky since it could be a Synth or a KBus
			while hasattr(value, 'o'): value = value.o
			assert isinstance(value, KBus), "%r is not a KBus!" % value
			return ('map', value._id)

	def __del__(self):
		# Use sc reference in case it has already quit()
		sc.send('/n_free', self._id)
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
		import collections
		self.voices = collections.deque()
	def play(self, pitch):
		now = time.time()
		with bundle:
			if not self.voices or now < self.voices[0]['time'] + 1.1:
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
	sc = scsynth.ScSynth()
	sc.boot()
	(send, bundle) = (sc.send, sc.bundled)
	def sendBundledMsg(*args):
		with bundle:
			send(*args)

	for sd in synthdefs.gen_synthdefs():
		send('/d_recv', sd.file_data())
		if getattr(sd, 'output_rate', None) is not None:
			output_rates[sd.name] = sd.output_rate
	#scsynth.boot()
	#send('/dumpOSC', 1); time.sleep(0.1)
	default = Group(); time.sleep(0.1)
	kbus0 = KBus()
	try:
		main()
	except:
		import traceback
		traceback.print_exc()
	finally:
		sc.quit()

