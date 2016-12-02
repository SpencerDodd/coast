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