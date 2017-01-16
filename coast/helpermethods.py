import os

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


def convert_int_to_hex(unencoded_input, padded_byte_size):
	"""
	Converts an integer to hexadecimal. Can specify byte-padding for proper formatting for
	message parameters

	:param padded_byte_size: number of bytes the output should be padded to
	:param unencoded_input: integer
	:return: hex-encoded output
	"""
	encoded = format(unencoded_input, "x")
	length = len(encoded)
	encoded = encoded.zfill(2 * padded_byte_size)
	return encoded.decode("hex")


def convert_hex_to_int(unencoded_input):
	"""
	Converts hex stream input into integer representation
	:param unencoded_input: hex input
	:return: integer representation of input
	"""
	return int(unencoded_input.encode("hex"), 16)


def indent_string(input_string, level_of_indentation):
	"""
	Indents every line of a given string by the given level of indentation * [TAB]

	:param input_string: string to be indented
	:param level_of_indentation: number of tabs to insert at the beginning of each line
	:return: indented string
	"""
	output_string = ""
	for line in input_string.split("\n"):
		output_string += "\n" + "\t"*level_of_indentation + line

	return output_string


def format_hex_output(hex_input):
	encoded = hex_input.encode("hex")
	unformatted = [encoded[x:x+2] for x in range(0, len(encoded), 2)]
	formatted = "0x" + " 0x".join(c for c in unformatted)
	return formatted


def make_dir(directory):
	"""
	Creates a directory if it doesn't exist
	:param directory: path to create
	"""
	if not os.path.exists(directory):
		os.mkdir(directory)