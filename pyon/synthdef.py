import StringIO
import struct


(ir, kr, ar) = (0, 1, 2)

defaults = {'amp': 1, 'attack': 0.001, 'decay': 1, 'freq': 440, 'i': 0, 'o': 0}


def make_packer():
	"""
	Return a tuple (io, data, pstr) where io is a StringIO, and data and pstr
	are lambdas that write packed data and Pascal strs, respectively, into io.
	"""
	io = StringIO.StringIO()
	data = lambda fmt, value: io.write(struct.pack('!' + fmt, value))
	pstr = lambda s: io.write(struct.pack('!B', len(s)) + s)
	return (io, data, pstr)

class SynthDef(object):
	ctx = None

	def __init__(self, name, *argNames):
		self.name = name
		self.params = []
		self.consts = []
		self.ugens = []
		self.argNames = argNames
		with self:
			for x in argNames:
				Param(x, defaults[x])
			self.control = UGen('Control', kr, [], [kr] * len(argNames))

	def __enter__(self):
		assert SynthDef.ctx is None, "no reentrant SynthDefs"
		SynthDef.ctx = self
		return self

	def __exit__(self, exc_type, value, traceback):
		SynthDef.ctx = None

	def getInputByArg(self, arg):
		return self.control[self.argNames.index(arg)]

	def data(self):
		"""
		Return the SynthDef's contents in SC's binary-packed synthdef format.
		Incidentally, this is pretty decent self-documentation for the format.
		"""
		(io, data, pstr) = make_packer()
		pstr(self.name)
		data('h', len(self.consts))
		for c in self.consts: data('f', float(c))

		data('h', len(self.params))
		for p in self.params: data('f', float(p[1]))
		data('h', len(self.params))
		for (i, p) in enumerate(self.params):
			pstr(p[0])
			data('h', i)

		data('h', len(self.ugens))
		for u in self.ugens:
			pstr(u.name)
			data('b', u.rate)
			data('h', len(u.inputs))
			data('h', len(u.outputs))
			data('h', u.special)
			for ispec in u.inputs:
				if type(ispec) is tuple:  # (UGen, output_idx)
					data('h', ispec[0].id)
					data('h', ispec[1])
				else:  # const_idx
					data('h', -1)
					data('h', ispec)
			for orate in u.outputs: data('b', orate)
		return io.getvalue()

	def register_const(self, value):
		"""Return a const index for the given int or float"""
		try:
			return self.consts.index(value)
		except ValueError:
			self.consts.append(value)
			return len(self.consts) - 1

	def file_data(self):
		"""Return the SynthDef's contents in synthdef file format."""
		return struct.pack('!iih', 0x53436766, 1, 1) + self.data() + '\x00\x00'


def Param(name, init):
	SynthDef.ctx.params.append((name, init))

class UGen(object):
	def __init__(self, name, rate, inputs, outputs=None, special=0):
		self.name = name
		self.rate = rate
		self.special = special
		self.inputs = map(self.process_input, inputs)
		self.outputs = outputs or ()
		self.id = len(SynthDef.ctx.ugens)
		SynthDef.ctx.ugens.append(self)
		if name == 'Out' and inputs[0] == 'o':
			SynthDef.ctx.output_rate = rate

	def __getitem__(self, key):
		assert type(key) is int
		return (self, key)

	def process_input(self, input):
		if type(input) is tuple: return input
		if type(input) is UGen: return input[0]
		if type(input) is str: return SynthDef.ctx.getInputByArg(input)
		assert type(input) in (int, float)
		return SynthDef.ctx.register_const(input)


def oscil(name, ugen, rate=ar):
	with SynthDef(name, 'freq', 'amp', 'o') as sd:
		sin = UGen(ugen, rate, ['freq', 0], [rate])
		op = UGen('BinaryOpUGen', rate, [sin, 'amp'], [rate], 2)
		UGen('Out', rate, ['o', op])
	return sd


if __name__ == '__main__':
	import hashlib, sys
	sine = oscil('sine', 'SinOsc', rate=ar).file_data()
	assert hashlib.md5(sine).hexdigest() == 'b7afb632d9cdbf5475cadb6a23ca27dd'

	delta = oscil('delta', 'Impulse', rate=kr).file_data()
	assert hashlib.md5(delta).hexdigest() == '793f1d7e473e7553e6708ec914ebef6b'

	with SynthDef('decay', 'i', 'attack', 'decay', 'o') as sd:
		decay2 = UGen('Decay2', kr, ['i', 'attack', 'decay'], [kr])
		UGen('Out', kr, ['o', decay2], [])
	decay = sd.file_data()
	assert hashlib.md5(decay).hexdigest() == '5d39ee9df3a7bf7608e49ff350cd70a4'

	print "all tests passed"
