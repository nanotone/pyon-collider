from pyon import synthdef
from pyon.synthdef import kr, ar, UGen

defs = {
	'sine': {'type': 'oscil', 'ugen': 'SinOsc', 'rate': ar},
	'delta': {'type': 'oscil', 'ugen': 'Impulse', 'rate': kr},
}

def gen_synthdefs():
	for (name, params) in defs.iteritems():
		fn = getattr(synthdef, params['type'])
		sd = fn(name, params['ugen'], params['rate'])
		yield sd

	with synthdef.SynthDef('decay', 'i', 'attack', 'decay', 'o') as decay:
		decay2 = UGen('Decay2', kr, ['i', 'attack', 'decay'], [kr])
		UGen('Out', kr, ['o', decay2[0]], [])
	yield decay


if __name__ == '__main__':
	import sys
	#make_oscil('sin', 'SinOsc', ar)
	#make_oscil('saw', 'Saw', ar)
	#make_oscil('ksin', 'SinOsc', kr)
	#make_oscil('delta', 'Impulse', kr)
	#sys.stdout.write( oscil('sine', 'SinOsc', ar).file_data() )
	pass
