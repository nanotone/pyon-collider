import re

repeater_re = re.compile(r'\(( [^)]* )\)  \s* \* \s*  (\d+)', re.VERBOSE)
solfege_re = re.compile(r"( [a-g] [_#]? )  ( [',]* )", re.VERBOSE)
note_re = re.compile(r"( [a-grsx] [_#]? )  ( '* )  ( \d* )", re.VERBOSE)

def parse(score):
	notes = list(gen_notes(score))
	notes.sort()
	return notes

def gen_notes(score):
	for line in re.split(r'\s*\n\s*', score.strip()):
		(instr, line) = line.split(':')

		# before we even expand repeaters, we need to convert to absolute octaves
		rel_solfege = [28]  # A0 is 0, A4 is 4*7. also, nonlocal
		def abs_solfege(match):
			diff = (ord(match.group(1)[0]) - 0x61) % 7 - rel_solfege[0] % 7
			if diff <= -4: diff += 7
			if diff >=  4: diff -= 7
			for c in match.group(2):
				if c == "'": diff += 7
				if c == ",": diff -= 7
			rel_solfege[0] += diff
			octave = rel_solfege[0] / 7  # octaves go from A to G
			return match.group(1) + "'" * octave
		line = re.sub(solfege_re, abs_solfege, line)

		line = re.sub(r'([^\s)]+)\s*\*', lambda m: '(' + m.group(1) + ')*', line)  # insert implied parens
		line = re.sub(repeater_re, lambda m: ' '.join((m.group(1),) * int(m.group(2))), line)  # expand repeats

		# do all the rest
		t_num = 0
		t_den = 1
		dur = 4 
		for note in line.strip().split():
			m = re.match(note_re, note)
			notename = m.group(1)
			if 'a' <= notename[0] <= 'g':
				noteval = ord(notename[0]) - 0x61
				noteval = (0, 2, 3, 5, 7, 8, 10)[noteval]  # aeolian mode
				if '_' in notename:
					noteval -= 1
				elif '#' in notename:
					noteval += 1
				noteval += 21 + 12 * len(m.group(2))
			else:
				noteval = {'r': 0, 'x': 1}.get(notename[0])
			if noteval is not None:
				t = 4.0 * t_num / t_den
				yield (t, instr, noteval)
			if m.group(3):
				dur = int(m.group(3))
			if t_den % dur:
				t_num *= dur
				t_den *= dur
			t_num += t_den / dur

if __name__ == '__main__':
	assert parse("""
one: (s8 c s c') * 2
two: (s4 x) * 2
""") == [(0.5, 'one', 72), (1.0, 'two', 1), (1.5, 'one', 84), (2.5, 'one', 72), (3.0, 'two', 1), (3.5, 'one', 84)]
	print "all tests passed"
