import struct

comma = ', '

def make_readers(f):
	return (
		lambda: struct.unpack('!i', f.read(4))[0],
		lambda: struct.unpack('!h', f.read(2))[0],
		lambda: struct.unpack('!b', f.read(1))[0],
		lambda: struct.unpack('!f', f.read(4))[0],
		lambda: f.read(struct.unpack('!B', f.read(1))[0]),
	)

calcRates = ["i-rate", "k-rate", "a-rate"]

def parse_file(f):
	(int32, int16, int8, float32, pstr) = make_readers(f)
	counter = lambda: xrange(int16())

	def iSpec():
		(one, two) = (int16(), int16())
		if one == -1:
			return str(consts[two])#'Const #%d' % two
		else:
			return 'UGen%d[%d]' % (one, two)

	assert int32() == 0x53436766
	assert int32() == 1
	for sdef in counter():
		print "Name:", pstr()
		consts = [float32() for k in counter()]
		print "Constants:", comma.join(map(str, consts))# str(float32()) for k in counter() )
		print "Param inits:", comma.join( str(float32()) for p in counter() )
		print "Param names:", comma.join( '#%(i)d=%(n)s' % {'n':pstr(), 'i':int16()} for n in counter() )
		print "UGens:"
		for u in counter():
			print "\tName:", pstr()
			print "\tRate:", calcRates[int8()]
			nInputs = counter()
			nOutputs = counter()
			print "\tSpecial:", int16()
			print "\tInputs:", comma.join( iSpec() for i in nInputs )
			print "\tOutputs:", comma.join( calcRates[int8()] for o in nOutputs )
			print

import sys

with open(sys.argv[1]) as f:
	parse_file(f)

