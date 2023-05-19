from collections import OrderedDict

def format_dict_to_str(dict):
    output = ""
    for key in dict:
        output += f'`{key}`: {dict[key]}\n'
    return output

def unformat_str_to_dict(str):
    lines = str.split('\n')
    dict = OrderedDict()
    for line in lines:
        if line.startswith('`'):
            key, value = line.split(': ')
            dict[key[1:-1]] = value
    return dict

