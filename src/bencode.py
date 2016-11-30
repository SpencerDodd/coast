import unittest

"""
This method recursively bencodes a given value or string of values, and returns 
the bencoded output.

Bencoding specifications are as follows (via The Bitorrent
Protocol Specification - http://bittorrent.org/beps/bep_0003.html):

	+-------+
	|Strings|
	+-------+
	Strings are length-prefixed base ten followed by a colon and the string. 
		For example 4:spam corresponds to 'spam'.
	
	+--------+
	|Integers|
	+--------+
	Integers are represented by an 'i' followed by the number in base 10 
	followed by an 'e'. 
		For example i3e corresponds to 3 and i-3e corresponds to -3. 
	Integers have no size limitation. i-0e is invalid. 
	All encodings with a leading zero, such as i03e, are invalid, 
	other than i0e, which of course corresponds to 0.
	
	+-----+
	|Lists|
	+-----+
	Lists are encoded as an 'l' followed by their elements (also bencoded) 
	followed by an 'e'. 
		For example l4:spam4:eggse corresponds to ['spam', 'eggs'].

	+------------+
	|Dictionaries|
	+------------+
	Dictionaries are encoded as a 'd' followed by a list of alternating 
	keys and their corresponding values followed by an 'e'. 
		For example, d3:cow3:moo4:spam4:eggse corresponds to 
		{'cow': 'moo', 'spam': 'eggs'} and d4:spaml1:a1:bee corresponds to 
		{'spam': ['a', 'b']}. 
	Keys must be strings and appear in sorted order (sorted as raw strings, 
	not alphanumerics).

"""

"""
Bencodes the given input
"""
def encode(unencoded_input):
	pass

"""
Returns the decoded result of a bencoded input
"""
def decode(bencoded_input):
	
	stack = list(bencoded_input)
	stack.reverse()
	objects_in_input = stack.count("e")

	for i in range(0, objects_in_input):
		if stack[i] == "e":
			current_type = stack[-1]

			# type is integer
			if current_type == "i":
				return stack[1]

		

"""
Unit tests
"""
class TestBencode(unittest.TestCase):

		def test_int(self):
			self.assertEqual("1", decode("i1e"))



if __name__ == "__main__":
	unittest.main()

	






















