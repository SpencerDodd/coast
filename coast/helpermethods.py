"""
Returns the pwd, minus one level of depth
"""

def one_directory_back(current_directory):
	rev_dir = current_directory[::-1]
	rev_result = ''
	result = ''

	for c in rev_dir:
		if c == '/':
			rev_result += rev_dir[rev_dir.index(c):]
			result = rev_result[::-1]

			return result


def convert_int_to_hex(unencoded_input):
	"""
	Converts an integer to hexadecimal. Safer than hex(integer) call.
	:param unencoded_input: integer
	:return: hex-encoded output
	"""
	encoded = format(unencoded_input, "x")
	length = len(encoded)
	encoded = encoded.zfill(length + length % 2)
	return encoded.decode("hex")


def convert_hex_to_int(unencoded_input):
	"""
	Converts hex stream input into integer representation
	:param unencoded_input: hex input
	:return: integer representation of input
	"""
	return int(unencoded_input.encode("hex"), 16)

