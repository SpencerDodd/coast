import os
import logging
import unittest
from auxillarymethods import one_directory_back

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

# Initialize logging
logger = logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
root_dir = one_directory_back(os.getcwd())
log_dir = os.path.join(root_dir, "logs")
handler = logging.FileHandler(os.path.join(log_dir, "log.txt"))
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

BENCODED_STRING_ERROR_SHORT = "Bencoded data invalid (string) [declared length was too short]"
BENCODED_STRING_ERROR_GENERAL = "Bencoded data invalid (string) [unencoded length not equal to declared]"
BENCODED_INT_ERROR_INPUT_VALUE = "Bencoded data invalid (int)"
"""
Bencodes the given input
"""
def encode(unencoded_input):
	pass


"""
Returns the bdecoded result of a bencoded input
"""
def bdecode(bencoded_input):

	logger.info("Decoding input: {}".format(bencoded_input))

	# we have reached the end of our input
	if bencoded_input == "":
		return bencoded_input

	for index,character in enumerate(bencoded_input):

		if character == "i":
			return bdecode_int(bencoded_input)
		
		elif is_int(character):
			return bdecode_string(bencoded_input)
		
		elif character == "l":
			logger.debug("Decoding list: {}".format(bencoded_input))
			next_object_index = 0
			return_list = []
			bencoded_list_contents = bencoded_input[1:-1]
			for idx,char in enumerate(bencoded_list_contents):
				remaining_list_contents = bencoded_list_contents[idx:]
				logger.debug("Iteration ({}): Current_char ({}) | next_object ({}) | remaining_list ({})".format(idx, char, next_object_index, remaining_list_contents))
				if idx == next_object_index:
					if char == "i":
						end_of_int_index = remaining_list_contents.find("e") + 1 + idx
						next_object_index = end_of_int_index
						return_list.append(bdecode(bencoded_list_contents[idx:end_of_int_index]))
						
						logger.debug("Decoding int: end_of_int_index ({}) | next_object_index ({})".format(end_of_int_index, next_object_index))
					
					elif is_int(char):
						length_of_string = int(bencoded_list_contents[idx:].split(":")[0])
						next_object_index = idx + length_of_string + 1 + int(bencoded_list_contents[idx:].split(":")[0])
						string_subsection = bencoded_list_contents[idx:next_object_index]
						remaining_area = bencoded_list_contents[next_object_index:]
						return_list.append(bdecode(string_subsection))

						logger.debug("Decoding string: length_of_string ({}) | next_object_index ({}) | string_subsection ({}) | remaining_area ({})".format(length_of_string, next_object_index, string_subsection, remaining_area))
					
					else:
						return_list.append(bdecode(remaining_list_contents))

			return return_list

		elif character == "d":
			logger.debug("Decoding dictionary: {}".format(bencoded_input))
			bencoded_list_contents = bencoded_input[1:-1]
			return_dict = {}

			logger.debug("Iteration ({}): Current_char ({}) | remaining_dict ({})".format("d", "c", bencoded_list_contents))
			
			lok = int(bencoded_list_contents.split(":")[0])
			lolok = len(str(lok))
			offset = lolok + 1

			key = bdecode_string(bencoded_list_contents[:lok+offset]) # key is string, int is length
			return_dict[key] = bdecode(bencoded_list_contents[lok+offset:])


			return return_dict


def bdecode_int(bencoded_int):
	try:
		end_of_int_index = bencoded_int.find("e")
		int_value = int(bencoded_int[1:end_of_int_index])
		return int_value
	
	except Exception as e:
		raise ValueError(BENCODED_INT_ERROR_INPUT_VALUE)
		print ("bencoded:({})\nendofint:({})\nintvalue:({})".format(end_of_int_index,int_value))


def bdecode_string(bencoded_string):
	# length of string
	los = int(bencoded_string.split(":")[0])
	# length of the length of string (decimal places)
	lolos = len(str(los))
	# first letter index
	fli = lolos + 1 # for ':' char
	# last letter index
	lli = lolos + los + 1 # for ':' char
	unenc_string = bencoded_string[fli:lli]
	# what is left in our string
	leftover = bencoded_string[lli:]
	# check if our unencoded string has more values than indicated by the
	#	los field, or if there are not enough values in the string as the
	#	amount allocated by the los field
	if leftover != "":
		raise ValueError(BENCODED_STRING_ERROR_SHORT)
	if los != len(unenc_string):
		raise ValueError(BENCODED_STRING_ERROR_GENERAL)
	
	else:
		return unenc_string

"""
Returns true if input string is a string representation of an int
"""
def is_int(string_input):
	try:
		int(string_input)
		return True
	except ValueError:
		return False
		

"""
Unit tests
"""
class TestBencode(unittest.TestCase):

	def test_is_int(self):
		self.assertEqual(True, is_int("1"))
		self.assertEqual(True, is_int("-1"))

	def test_int(self):
		self.assertEqual(1, bdecode("i1e"))
		self.assertEqual(-1, bdecode("i-1e"))
		self.assertEqual(100, bdecode("i100e"))
		
		# Error raising
		with self.assertRaises(ValueError) as context:
			bdecode("i10ae")
		self.assertTrue(BENCODED_INT_ERROR_INPUT_VALUE in context.exception)

	def test_string(self):
		self.assertEqual("test", bdecode("4:test"))
		self.assertEqual("holy guacamole", bdecode("14:holy guacamole"))
		with self.assertRaises(ValueError) as context:
			bdecode("3:test")
		self.assertTrue(BENCODED_STRING_ERROR_SHORT in context.exception)
		with self.assertRaises(ValueError) as context:
			bdecode("5:test")
		self.assertTrue(BENCODED_STRING_ERROR_GENERAL in context.exception)

	def test_list(self):
		self.assertEqual([1, 2, 3, 4], bdecode("li1ei2ei3ei4ee"))
		self.assertEqual([1, "a", 2, "b"], bdecode("li1e1:ai2e1:be"))
		self.assertEqual([1, [2, 3, 4]], bdecode("li1eli2ei3ei4eee"))

	def test_dict(self):
		self.assertEqual({"key": "value"}, bdecode("d3:key5:valuee"))
		self.assertEqual({"key": ["value", 1]}, bdecode("d3:keyl5:valuei1eee"))
	
if __name__ == "__main__":
	unittest.main()

	






















