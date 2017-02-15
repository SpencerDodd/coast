import os

"""
Returns the pwd, minus one level of depth
"""

def one_directory_back(current_directory):
	rev_dir = current_directory[::-1]
	rev_result = ''
	result = ''

	for index,c in enumerate(rev_dir):
		if c == '/' and index != 0:
			rev_result += rev_dir[index:]
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


def tally_messages_by_type(list_of_messages):
	"""
	Tallies the number of each type of message present in a given list
	:param list_of_messages: self-explanatory
	:return: string
	"""
	output_string = ""
	type_by_id = {
		0: ["choke", 0],
		1: ["unchoke", 0],
		2: ["interested", 0],
		3: ["not_interested", 0],
		4: ["have", 0],
		5: ["bitfield", 0],
		6: ["request", 0],
		7: ["piece", 0],
		8: ["cancel", 0],
		9: ["port", 0],
		19: ["handshake", 0],
		20: ["extended_handshake", 0],
		255: ["keep_alive", 0]
	}
	for message in list_of_messages:
		type_by_id[message.get_message_id()][1] += 1

	for totals in type_by_id.values():
		output_string += totals[0] + ": " + str(totals[1]) + ", "

	return output_string
