import json
import sys
import os
from stop_exec import StopExecution


def _setup(count=0, datatype=None):
    d = {'count': count}
    if datatype is not None:
        d['datatypes'] = [datatype]
    else:
        d['datatypes'] = []
    return d


def _count_tag(tag_name: str, tags: dict) -> None:
    try:
        count = tags[tag_name]['count']
        tags[tag_name]['count'] = count + 1
    except KeyError:
        tags[tag_name] = _setup(count=1)


def _record_datatype(tag_name, tags: dict, datatype) -> None:
    datatype = str(datatype).replace("<class '", "").replace("'>", "")
    try:
        datatypes = tags[tag_name]['datatypes']
        if datatype not in datatypes:
            datatypes.append(datatype)
    except KeyError:
        tags[tag_name] = _setup(datatype=datatype)


def _output(tag_set: dict, out_file_path, encoding) -> None:
    with open(out_file_path, 'w', encoding=encoding) as out_file:
        out_file.write("tag,count,datatypes\n")
        for tag in tag_set:
            datatypes = _format_list_content(tag_set[tag]['datatypes'])
            out_file.write(tag + "," + str(tag_set[tag]['count']) + ',' + datatypes + "\n")
    print('Done')


def _format_list_content(list_in):
    out = ''
    for i, l in enumerate(list_in):
        out = out + l
        if i < len(list_in) - 1:
            out = out + ';'
    return out


def _set_file(text, mandatory=False):
    file_path = input(f"path to {text}: ")
    if mandatory:
        if os.path.isfile(file_path):
            return file_path
        else:
            _set_file(f'Provided file does not exist. Please provide a valid path to the {text}: ', True)
    else:
        return file_path


def _traverse(root, name: str, tags: dict) -> None:
    _record_datatype(name, tags, type(root))
    _count_tag(name, tags)
    if isinstance(root, list) | isinstance(root, dict):  # check if passed element is a list or dictionary
        i = 0                                            # counter variable for sibling elements
        for child in root:                               # cycle through the children of root element
            if i > 0:                                    # i > 0 means this is sibling element and last name element needs removing
                try:
                    name = name[:name.rindex(".")]
                except ValueError:
                    name = name
                    print('ValueError: ' + name)

            if isinstance(root, list):
                name = name + '.[]'
                _traverse(child, name, tags)

            else:
                name = name + "." + child
                _traverse(root[child], name, tags)
            i = i + 1


def run(input_file: str = None, output_file: str = None, sort=False, encoding='utf-8'):
    tags = {}
    if input_file is None:
        input_file = _set_file('file to analyse', True)
    if not os.path.isfile(input_file):
        print('Provided input file does not exist.')
        input_file = _set_file('file to analyse', True)
    if output_file is None:
        output_file = _set_file('output file')

    if input_file is not None and output_file is not None:
        try:
            with open(input_file, 'r', encoding=encoding) as file:
                data = json.load(file)
        except json.JSONDecodeError as e:
            print(
                "Input file could not be decoded. Could be because it's not a valid JSON file or it contains characters that cannot be decoded with the provided encoding scheme. Exiting script. JSONDecodeError: " + str(
                    e))
            raise StopExecution
        _traverse(data, 'root', tags)
        if sort:
            tags = dict(sorted(tags.items()))
        try:
            _output(tags, output_file, encoding)
        except IOError as e:
            print("Output file could not be written. Dumping to cache and exiting script. IOError: " + str(e))
            with open('cache.txt', 'w', encoding=encoding) as cache:
                cache.write(str(tags))
            raise StopExecution
    else:
        print("Input file or output file missing. Exiting script.")
        raise StopExecution