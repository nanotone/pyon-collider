class Pool(object):
	def __init__(self, firstId=1):
		self.next = firstId
		self.reuse = set()
	def get(self):
		try:
			return self.reuse.pop()
		except KeyError:
			self.next += 1
			return self.next - 1
	def put(self, id):
		if id == self.next - 1:
			self.next = id
			try:
				while True:
					self.reuse.remove(self.next - 1)
					self.next -= 1
			except KeyError: pass
		else:
			self.reuse.add(id)

if __name__ == '__main__':
	p = Pool()
	assert p.next == 1
	assert p.get() == 1 and p.next == 2
	assert p.get() == 2 and p.next == 3
	p.put(2)
	assert p.next == 2
	assert p.get() == 2 and p.next == 3
	p.put(1)
	assert p.next == 3
	p.put(2)
	assert p.next == 1
	print "all tests pass"
