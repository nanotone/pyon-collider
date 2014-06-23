from pyon.synthdef import kr, ar, agen, kgen, synthdef, oscil

oscils = {
	'sin': {'ugen': 'SinOsc', 'rate': ar},
	'ksin': {'ugen': 'SinOsc', 'rate': kr},
	'delta': {'ugen': 'Impulse', 'rate': kr},
}

def gen_synthdefs():
	for (name, params) in oscils.iteritems():
		sd = oscil(name, params['ugen'], params['rate'])
		yield sd

	@synthdef
	def decay(i, decay, out):
		return kgen.Decay(i, decay)
	yield decay
	@synthdef
	def decay2(i, attack, decay, out):
		return kgen.Decay2(i, attack, decay)
	yield decay2

	@synthdef
	def kick():
		return agen.SinOsc(kgen.XLine(60, 20, 0.5)) * kgen.Line(1, 0, 0.5) + agen.LPF(agen.WhiteNoise(), 300) * kgen.Line(1, 0, 0.03)
	yield kick

if __name__ == '__main__':
	import sys
	#make_oscil('sin', 'SinOsc', ar)
	#make_oscil('saw', 'Saw', ar)
	#make_oscil('ksin', 'SinOsc', kr)
	#make_oscil('delta', 'Impulse', kr)
	#sys.stdout.write( oscil('sin', 'SinOsc', ar).file_data() )
	pass
