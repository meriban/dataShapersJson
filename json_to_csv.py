import csv
import json
from copy import deepcopy
from json import JSONDecodeError


def _get_headers(file_path, has_headers=True, path_index=0, dt_index=2, exclusions=('dict', 'list'),
                 encoding='utf-8'):
    headers = []
    lists_list = []
    with open(file_path, 'r', encoding=encoding) as file:
        reader = csv.reader(file)
        for index, row in enumerate(reader):
            if index == 0:
                if has_headers:
                    continue
            datatypes = row[dt_index].split(';')
            path = row[path_index]
            if 'list' in datatypes:
                lists_list.append(path)
            if _check_intersection(datatypes,
                                   exclusions):  # todo: this is not fool proof if say an element can be list or string
                pass
            else:
                headers.append(path)
    lists = {}
    for li in lists_list:
        lists[li] = {}
        for h in headers:
            if li in h:
                lists[li][h] = ''
    return headers, lists


def _check_intersection(list1, list2):
    return len(set(list1) & set(list2)) > 0


def _traverse(root, name: str, base: str, target_name: str, lists_dict, out=None):
    if out is None:
        out = {}
    is_target = False
    if name == target_name or name == base:
        is_target = True
    if isinstance(root, dict):
        i = 0  # counter variable for sibling elements
        for child in root:  # cycle through the children of root element
            name_child = name + "." + child
            ret = _traverse(root[child], name_child, base, target_name, lists_dict, out=out)
            if isinstance(ret, str):
                out[name_child] = ret
            if isinstance(root[child], list):
                out = _unpack(out, ret)
            i = i + 1
        return out

    elif isinstance(root, list):
        i = 0  # counter variable for sibling elements
        list_headers = deepcopy(lists_dict[name])
        for child in root:  # cycle through the children of root element
            _out = {}
            name_child = name + '.[]'
            ret = _traverse(child, name_child, base, target_name, lists_dict, out=_out)
            if isinstance(ret, str):
                try:
                    prev_value = out[name]
                    if prev_value != '':
                        out[name] = prev_value + ';' + ret
                except KeyError:
                    out[name] = ret
            else:
                list_headers = _join(list_headers, _out, i, is_target)

            i = i + 1
        return list_headers
    else:
        return _format_value(root)


def _format_value(data_to_write):
    if isinstance(data_to_write, str):
        if ',' in data_to_write:
            data_to_write = '"' + data_to_write + '"'
        return data_to_write
    if isinstance(data_to_write, int) or isinstance(data_to_write, float) or isinstance(data_to_write, bool):
        return str(data_to_write)
    if data_to_write is None:
        return ''


def _join(parent_dict, child_dict, index, is_target_level=False):
    for key in parent_dict.keys():
        try:
            child_value = child_dict[key]
        except KeyError:
            child_value = ''
        if index == 0:
            parent_dict[key] = [child_value]
        else:
            parent_value = parent_dict[key]
            if is_target_level:
                if not isinstance(parent_value, list):
                    raise ValueError('Not a list')
                else:
                    parent_value.append(child_value)
                    parent_dict[key] = parent_value
            else:
                if not isinstance(parent_value, str):
                    parent_value = parent_value[0]
                else:
                    raise ValueError('Not a string')
                new_value = parent_value + ';' + child_value
                parent_dict[key] = [new_value]
    return parent_dict


def _unpack(parent_dict, child_dict):
    for key in child_dict.keys():
        if key not in parent_dict.keys():
            if isinstance(cv := child_dict[key], list):
                if len(cv) > 1:
                    parent_dict[key] = cv
                elif len(cv) == 1:
                    parent_dict[key] = cv[0]
                else:
                    raise ValueError('Empty list')
            else:
                parent_dict[key] = child_dict[key]
        else:
            raise ValueError('Key already exists')
    return parent_dict


def _output(_data, headers, output_file, head=False):
    with open(output_file, 'a', encoding='utf-8', newline='') as out_file:
        writer = csv.DictWriter(out_file, fieldnames=headers)
        if head:
            writer.writeheader()
        else:
            writer.writerow(_data)


def run(json_file, header_file, output_file, base, target, encoding='utf-8'):
    headers, lists_dict = _get_headers(header_file)

    with open(json_file, 'r', encoding=encoding) as file:
        try:
            data = json.load(file)
            result = _traverse(data, 'root', base, target, lists_dict)
        except JSONDecodeError:
            print('JSONDecodeError')
    _format_output(result, base, target, headers, output_file)


def _format_output(result, base, target, headers, output_file):
    _output(None, headers, output_file, head=True)
    constants = []
    base_fields = []
    target_fields = []
    base_list = base + '.[]'
    target_list = target + '.[]'
    for h in headers:
        value = result[h]
        if not isinstance(value, list):
            constants.append(h)
            continue
        if target_list in h:
            target_fields.append(h)
            continue
        if base_list in h:
            base_fields.append(h)
            continue
        raise ValueError('Field not a constant, in base or target')
    base_length = len(result[base_fields[0]])
    base_counter = 0
    row = {}
    for constant in constants:
        row[constant] = result[constant]
    while base_counter < base_length:
        for base_field in base_fields:
            row[base_field] = result[base_field][base_counter]
        if isinstance(x := result[target_fields[0]][base_counter], list):
            target_length = len(x)
            target_counter = 0
            while target_counter < target_length:
                for target_field in target_fields:
                    row[target_field] = result[target_field][base_counter][target_counter]
                _output(row, headers, output_file)
                target_counter += 1
        else:
            for target_field in target_fields:
                row[target_field] = result[target_field][base_counter]
            _output(row, headers, output_file)
        base_counter += 1
