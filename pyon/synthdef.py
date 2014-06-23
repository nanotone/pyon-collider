import StringIO
import struct


(ir, kr, ar) = (0, 1, 2)

defaults = {'amp': 1, 'attack': 0.001, 'decay': 1, 'freq': 440, 'i': 0, 'out': 0}


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
			if argNames:
				self.control = UGen('Control', rate=kr, outputs=[kr] * len(argNames))

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
		for (i, ugen) in enumerate(self.ugens):
			ugen.id = i

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
	def __init__(self, name, *inputs, **kwargs):
		self.name = name
		self.rate = kwargs.get('rate')
		if self.rate is None:
			self.rate = max(i.rate if isinstance(i, UGen) else kr for i in inputs)
		self.special = kwargs.get('special', 0)
		self.inputs = map(self.process_input, inputs)
		outputs = kwargs.get('outputs')
		if not outputs:
			outputs = () if self.name == 'Out' else [self.rate]
		self.outputs = outputs
		SynthDef.ctx.ugens.append(self)
		if name == 'Out' and inputs[0] == 'out':
			SynthDef.ctx.output_rate = self.rate

	def __getitem__(self, key):
		assert type(key) is int
		return (self, key)

	def __add__(self, other):
		# see if we can upgrade a mulOp BinaryOpUGen to a MulAdd
		if self.name == 'BinaryOpUGen' and self.special == 2:
			self.name = 'MulAdd'
			self.rate = max(self.rate, other.rate if isinstance(other, UGen) else kr)
			self.inputs.append(self.process_input(other))
			self.outputs = [self.rate]
			self.special = 0
			SynthDef.ctx.ugens.remove(self)
			SynthDef.ctx.ugens.append(self)  # move MulAdd to end
			return self
		return UGen('BinaryOpUGen', self, other, special=0)
	def __radd__(self, other):
		return UGen('BinaryOpUGen', other, self, special=0)

	def __sub__(self, other):
		return UGen('BinaryOpUGen', self, other, special=1)
	def __rsub__(self, other):
		return UGen('BinaryOpUGen', other, self, special=1)

	def __mul__(self, other):
		return UGen('BinaryOpUGen', self, other, special=2)
	def __rmul__(self, other):
		return UGen('BinaryOpUGen', other, self, special=2)

	def process_input(self, input):
		if type(input) is tuple: return input
		if type(input) is UGen: return input[0]
		if type(input) is str: return SynthDef.ctx.getInputByArg(input)
		assert type(input) in (int, float), "Input %r has illegal type %r" % (input, type(input))
		return SynthDef.ctx.register_const(input)

class UGenSugar(object):
	defaults = {
		'LPF': (0, 440),
		'Line': (0, 1, 1, 0),
		'MulAdd': (None, 1, 0),
		'SinOsc': (440, 0),
		'WhiteNoise': (),
		'XLine': (1, 2, 1, 0),
	}
	def __init__(self, rate):
		self.rate = rate
	def __getattr__(self, name):
		assert name[0].isupper()
		arg_defaults = UGenSugar.defaults.get(name)
		def ctor(*inputs):
			if arg_defaults:
				assert len(inputs) <= len(arg_defaults), "%s UGen takes %d argument(s) (%d given)" % (name, len(arg_defaults), len(inputs))
				if arg_defaults and len(inputs) < len(arg_defaults):
					inputs += arg_defaults[len(inputs):]
			return UGen(name, *inputs, rate=self.rate)
		setattr(self, name, ctor)
		return ctor
	def __getitem__(self, key):
		return getattr(self, key)
agen = UGenSugar(ar)
kgen = UGenSugar(kr)


def oscil(name, ugen, rate=ar):
	with SynthDef(name, 'freq', 'amp', 'out') as sd:
		sin = UGen(ugen, 'freq', 0, rate=rate)
		UGen('Out', 'out', sin * 'amp')
	return sd

def synthdef(f):
	fc = f.func_code
	argnames = fc.co_varnames[:fc.co_argcount]
	with SynthDef(f.func_name, *argnames) as sd:
		result = f(*argnames)
		if result:
			UGen('Out', 'out' if 'out' in argnames else 0, result)
	return sd

if __name__ == '__main__':
	import hashlib, sys
	sine = oscil('sine', 'SinOsc', rate=ar).file_data()
	assert hashlib.md5(sine).hexdigest() == '9e53e95ee9fce31b2feb613dec4786b3'

	delta = oscil('delta', 'Impulse', rate=kr).file_data()
	assert hashlib.md5(delta).hexdigest() == '2a23957a5c6dcca1b28d157a1278f045'

	@synthdef
	def decay(i, attack, decay, out):
		return kgen.Decay2(i, attack, decay)
	assert hashlib.md5(decay.file_data()).hexdigest() == '04199c04e75c09f972a64632fa9ac22a'

	@synthdef
	def kick():
		return agen.SinOsc(60) * kgen.Line(1, 0, 1, 2)
	assert hashlib.md5(kick.file_data()).hexdigest() == '2269b4df827a8614ee2862961d4be4ef'

	@synthdef
	def muladd():
		return kgen.SinOsc(60) * 2 + 1
	assert hashlib.md5(muladd.file_data()).hexdigest() == '001c1f74dc57231d7a1c441959db2e00'

	print "all tests passed"
