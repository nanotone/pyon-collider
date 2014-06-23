import itertools
import time

import pool
import scsynth

output_rates = {}


class Group(object):
	def __init__(self, engine):
		self._id = engine.node_pool.get()
		engine.send('/g_new', self._id, 0, 0)


class KBus(object):
	def __init__(self, engine):
		self.engine = engine 
		self._id = engine.kbus_pool.get()

	def set(self, value):
		self.engine.send_bundled_msg('/c_set', self._id, value)

	def __del__(self):
		self.engine.kbus_pool.put(self._id)


class Synth(object):
	def __init__(self, engine, sd_name, parent, **kwargs):
		self._engine = engine
		self._id = engine.node_pool.get()
		if output_rates.get(sd_name) == 1: # control bus output
			if 'out' not in kwargs:
				kwargs['out'] = engine.kbus()
		with engine.bundle:
			# setattr ALL the kwargs! But combine the sets and maps for efficiency
			snew = ['/s_new', sd_name, self._id, 0, parent._id]
			mapping = {}
			for (name, value) in kwargs.iteritems():
				object.__setattr__(self, name, value)
				setter = self._set(name, value)
				if setter:
					if setter[0] == 'set':
						snew.extend((name, setter[1]))
					elif setter[0] == 'map':
						mapping[name] = setter[1]
			engine.send(*snew)
			if mapping:
				engine.send('/n_map', self._id, *itertools.chain( *mapping.items() ))

	def __setattr__(self, name, value):
		object.__setattr__(self, name, value)
		setter = self._set(name, value)
		if setter:
			if setter[0] == 'set':
				self._engine.send('/n_set', self._id, name, setter[1])
			elif setter[0] == 'map':
				with self._engine.bundle:
					self._engine.send('/n_map', self._id, name, setter[1])

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
		elif name == 'out' and isinstance(value, KBus):
			return ('set', value._id)
		else:
			# Assume we want to n_map a kr-param to a kr-synth's output
			# This is a bit tricky since it could be a Synth or a KBus
			while hasattr(value, 'out'): value = value.out
			assert isinstance(value, KBus), "%r is not a KBus!" % value
			return ('map', value._id)

	def __del__(self):
		# Use sc reference in case it has already quit()
		self._engine.sc.send('/n_free', self._id)
		self._engine.node_pool.put(self._id)


class ScEngine(object):
	def __init__(self, sc=None):
		self.sc = sc or scsynth.ScSynth()
		self.node_pool = pool.Pool()
		self.kbus_pool = pool.Pool(0)
		if not self.sc.booted:
			self.sc.boot()

		self.send = self.sc.send
		self.bundle = self.sc.bundled
		self.default = Group(self)
		time.sleep(0.1)
		self.kb0 = KBus(self)

	def kbus(self, value=None):
		kb = KBus(self)
		if value is not None:
			kb.set(value)
		return kb

	def synth(self, sd_name, parent=None, **kwargs):
		if not parent:
			parent = self.default
		return Synth(self, sd_name, parent, **kwargs)

	def send_synthdef(self, synthdef):
		self.sc.send('/d_recv', synthdef.file_data())
		if getattr(synthdef, 'output_rate', None) is not None:
			output_rates[synthdef.name] = synthdef.output_rate

	def shutdown(self):
		self.sc.quit()
