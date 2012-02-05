import StringIO
import struct

(ir, kr, ar) = (0, 1, 2)

defaults = {'amp': 1, 'attack': 0.001, 'decay': 1, 'freq': 440, 'i': 0, 'o': 0}

def make_packer():
	io = StringIO.StringIO()
	data = lambda fmt, value: io.write(struct.pack('!' + fmt, value))
	pstr = lambda s: io.write(struct.pack('!B', len(s)) + s)
	return (io, data, pstr)

class SynthDef(object):
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
		global current_sd
		current_sd = self

	def __exit__(self, exc_type, value, traceback):
		global current_sd
		current_sd = None

	def getInputByArg(self, arg):
		return self.control[self.argNames.index(arg)]

	def getData(self):
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
				if type(ispec) is tuple:
					data('h', ispec[0].id)
					data('h', ispec[1])
				else:
					data('h', -1)
					data('h', ispec)
			for orate in u.outputs: data('b', orate)

		self.data = io.getvalue()
		return self.data

	def register_const(self, value):
		try:
			return self.consts.index(value)
		except ValueError:
			self.consts.append(value)
			return len(self.consts) - 1

def Param(name, init):
	current_sd.params.append((name, init))

class UGen(object):
	def __init__(self, name, rate, inputs, outputs, special=0):
		self.name = name
		self.rate = rate
		self.special = special
		self.inputs = map(self.process_input, inputs)
		self.outputs = outputs
		self.id = len(current_sd.ugens)
		current_sd.ugens.append(self)

	def __getitem__(self, key):
		assert type(key) is int
		return (self, key)

	def process_input(self, input):
		if type(input) is tuple: return input
		if type(input) is str: return current_sd.getInputByArg(input)
		assert type(input) in (int, float)
		return current_sd.register_const(input)


def oscil(name, ugen, rate=ar):
	oscil = SynthDef(name, 'freq', 'amp', 'o')
	with oscil:
		sin = UGen(ugen, rate, ['freq', 0], [rate])
		amp = UGen('BinaryOpUGen', rate, [sin[0], 'amp'], [rate], 2)
		UGen('Out', rate, ['o', amp[0]], [])
	return oscil.getData()

def filewrap(data):
	return struct.pack('!iih', 0x53436766, 1, 1) + data + '\x00\x00'


if __name__ == '__main__':
	import hashlib, sys
	sine = filewrap(oscil('sine', 'SinOsc', rate=ar))
	assert hashlib.md5(sine).hexdigest() == 'b7afb632d9cdbf5475cadb6a23ca27dd'

	delta = filewrap(oscil('delta', 'Impulse', rate=kr))
	assert hashlib.md5(delta).hexdigest() == '793f1d7e473e7553e6708ec914ebef6b'

	decay = SynthDef('decay', 'i', 'attack', 'decay', 'o')
	with decay:
		decay2 = UGen('Decay2', kr, ['i', 'attack', 'decay'], [kr])
		UGen('Out', kr, ['o', decay2[0]], [])
	decay = filewrap(decay.getData())
	assert hashlib.md5(decay).hexdigest() == '5d39ee9df3a7bf7608e49ff350cd70a4'

	print "all tests passed"
