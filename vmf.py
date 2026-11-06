import copy
import hashlib
import math
import os
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path


TOKEN = re.compile(r'\s+|//[^\r\n]*|"[^"\r\n]*"|[{}]|[^\s{}"]+')


def parse(text):
    tokens = []
    position = 0
    for match in TOKEN.finditer(text):
        if match.start() != position:
            raise ValueError(f'Invalid VMF token at {position}')
        position = match.end()
        token = match.group()
        if not token.isspace() and not token.startswith('//'):
            if token.startswith('"'):
                token = token[1:-1]
                tokens.append(('value', token))
            else:
                tokens.append(('brace' if token in '{}' else 'value', token))
    if position != len(text):
        raise ValueError(f'Invalid VMF token at {position}')
    index = 0
    def block(nested=False):
        nonlocal index
        pairs = []
        while index < len(tokens):
            kind, key = tokens[index]
            index += 1
            if kind == 'brace' and key == '}':
                if nested:
                    return pairs
                raise ValueError('Unexpected closing brace')
            if kind != 'value' or index == len(tokens):
                raise ValueError('VMF key has no value')
            value_kind, value = tokens[index]
            index += 1
            if value_kind == 'brace':
                if value != '{':
                    raise ValueError('Unexpected closing brace')
                value = block(True)
            pairs.append([key, value])
        if nested:
            raise ValueError('Unclosed VMF block')
        return pairs
    return block()


def dump(pairs, depth=0):
    lines = []
    def quote(value):
        if not isinstance(value, str) or any(character in value for character in '\x00\n\r"'):
            raise ValueError('This Hammer VMF format does not support quotes, line breaks or NULs inside scalar values')
        return '"' + value + '"'
    for key, value in pairs:
        if isinstance(value, list):
            lines.extend(['\t' * depth + quote(key), '\t' * depth + '{', dump(value, depth + 1).rstrip('\n'), '\t' * depth + '}'])
        else:
            lines.append('\t' * depth + quote(key) + ' ' + quote(value))
    return '\n'.join(lines) + '\n'


def walk(pairs, kind='root'):
    yield kind, pairs
    for key, value in pairs:
        if isinstance(value, list):
            yield from walk(value, key)


def properties(pairs):
    return {key: value for key, value in pairs if isinstance(value, str)}


def set_property(pairs, key, value):
    if value is not None and '\\' in str(value):
        raise ValueError('Hammer does not reliably round-trip backslashes in VMF values. Use forward slashes in paths; raw VMF tools preserve existing serialized values.')
    matches = [index for index, pair in enumerate(pairs) if pair[0] == key and isinstance(pair[1], str)]
    if len(matches) > 1:
        raise ValueError(f'{key} has duplicate values; use replace_node to preserve explicit ordering')
    if value is None:
        if matches:
            pairs.pop(matches[0])
    elif matches:
        pairs[matches[0]][1] = str(value)
    else:
        pairs.append([key, str(value)])


def node(pairs, identifier):
    found = [(kind, data) for kind, data in walk(pairs) if properties(data).get('id') == str(identifier)]
    if len(found) != 1:
        raise ValueError(f'Expected one VMF object with id {identifier}, found {len(found)}')
    return found[0]


def validate(pairs):
    identifiers = []
    for kind, data in walk(pairs):
        props = properties(data)
        if 'id' in props:
            identifier = int(props['id'])
            if identifier < 1:
                raise ValueError('VMF object ids must be positive integers')
            identifiers.append(identifier)
        if kind == 'solid' and sum(key == 'side' for key, value in data) < 4:
            raise ValueError('A solid needs at least four sides')
        if kind == 'side' and 'plane' in props:
            values = [float(number) for number in re.findall(r'[-+\d.eE]+', props['plane'])]
            if len(values) != 9 or not all(math.isfinite(number) for number in values):
                raise ValueError('A side plane needs three finite 3D points')
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('VMF object ids must be unique')
    if sum(key == 'world' for key, value in pairs) != 1:
        raise ValueError('A VMF map needs exactly one world block')
    if parse(dump(pairs)) != pairs:
        raise ValueError('VMF round-trip validation failed')


def load(path):
    path = Path(path).resolve()
    if path.suffix.lower() != '.vmf':
        raise ValueError('Expected a .vmf path')
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'cp1254', 'cp1252'):
        try:
            return path, raw, parse(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError('Unsupported map encoding')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, object_id=None, query='', offset=0, limit=100, full=False):
    path, raw, pairs = load(path)
    if full:
        return {'path': str(path), 'sha256': digest(raw), 'vmf': dump(pairs)}
    if object_id is not None:
        kind, data = node(pairs, object_id)
        return {'path': str(path), 'sha256': digest(raw), 'kind': kind, 'pairs': data}
    objects = []
    counts = Counter()
    for kind, data in walk(pairs):
        counts[kind] += 1
        props = properties(data)
        if 'id' in props and query.casefold() in (kind + ' ' + ' '.join(props.values())).casefold():
            objects.append({'kind': kind, **props})
    if offset < 0 or not 1 <= limit <= 1000:
        raise ValueError('offset must be nonnegative and limit must be between 1 and 1000')
    return {'path': str(path), 'sha256': digest(raw), 'counts': dict(counts), 'matching_objects': len(objects), 'objects': objects[offset:offset + limit], 'next_offset': offset + limit if offset + limit < len(objects) else None}


def write(path, pairs, expected_sha256=None, create=False):
    path = Path(path).resolve()
    if path.suffix.lower() != '.vmf':
        raise ValueError('Expected a .vmf path')
    validate(pairs)
    text = dump(pairs)
    raw = text.encode('utf-8')
    old = None
    backup = None
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as output:
            output.write(raw)
    else:
        old = path.read_bytes()
        if not expected_sha256 or digest(old) != expected_sha256:
            raise ValueError('Map changed or expected_sha256 is missing. Read the map again before editing.')
        for encoding in (('utf-8-sig',) if old.startswith(b'\xef\xbb\xbf') else ('utf-8', 'cp1254', 'cp1252')):
            try:
                old.decode(encoding)
            except UnicodeDecodeError:
                continue
            raw = text.encode(encoding)
            break
        backup_dir = path.parent / '.hammer-mcp-backups'
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f'{path.stem}.{digest(old)}.vmf'
        if not backup.exists():
            with backup.open('xb') as output:
                output.write(old)
        if backup.read_bytes() != old:
            raise RuntimeError('Backup integrity check failed')
        descriptor, temporary = tempfile.mkstemp(prefix=path.stem + '.', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(descriptor, 'wb') as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            shutil.copystat(path, temporary)
            if path.read_bytes() != old:
                raise ValueError('Map changed during editing; the original file was retained')
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {**read(path, limit=1), 'backup': str(backup) if backup else None}


def create(path):
    pairs = [['versioninfo', [['editorversion', '400'], ['editorbuild', '8873'], ['mapversion', '1'], ['formatversion', '100'], ['prefab', '0']]], ['visgroups', []], ['viewsettings', [['bSnapToGrid', '1'], ['bShowGrid', '1'], ['bShowLogicalGrid', '0'], ['nGridSpacing', '64'], ['bShow3DGrid', '0']]], ['world', [['id', '1'], ['mapversion', '1'], ['classname', 'worldspawn'], ['skyname', 'sky_day01_01']]], ['cameras', [['activecamera', '-1']]], ['cordons', [['active', '0']]]]
    return write(path, pairs, create=True)


def vector(values):
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        raise ValueError('Expected three coordinates')
    result = [float(value) for value in values]
    if not all(math.isfinite(value) for value in result):
        raise ValueError('Coordinates must be finite')
    return result


def numbers(values):
    return ' '.join(f'{value:.9g}' for value in values)


def box(minimum, maximum, material, allocate):
    x0, y0, z0 = vector(minimum)
    x1, y1, z1 = vector(maximum)
    if x0 >= x1 or y0 >= y1 or z0 >= z1:
        raise ValueError('Box minimum must be below maximum on every axis')
    planes = [((x0, y1, z1), (x1, y1, z1), (x1, y0, z1)), ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0)), ((x0, y1, z1), (x0, y0, z1), (x0, y0, z0)), ((x1, y1, z0), (x1, y0, z0), (x1, y0, z1)), ((x1, y1, z1), (x0, y1, z1), (x0, y1, z0)), ((x1, y0, z0), (x0, y0, z0), (x0, y0, z1))]
    result = [['id', str(allocate())]]
    for index, plane in enumerate(planes):
        uaxis, vaxis = (('[1 0 0 0] 0.25', '[0 -1 0 0] 0.25') if index < 2 else ('[0 1 0 0] 0.25', '[0 0 -1 0] 0.25') if index < 4 else ('[1 0 0 0] 0.25', '[0 0 -1 0] 0.25'))
        result.append(['side', [['id', str(allocate())], ['plane', ' '.join('(' + numbers(point) + ')' for point in plane)], ['material', str(material)], ['uaxis', uaxis], ['vaxis', vaxis], ['rotation', '0'], ['lightmapscale', '16'], ['smoothing_groups', '0']]])
    return result


def translate(pairs, delta):
    delta = vector(delta)
    for kind, data in walk(pairs):
        props = properties(data)
        for key in ('origin', 'startposition'):
            if key in props:
                point = [float(value) for value in re.findall(r'[-+\d.eE]+', props[key])]
                if len(point) != 3:
                    raise ValueError(f'Cannot translate {key}')
                shifted = numbers([point[index] + delta[index] for index in range(3)])
                set_property(data, key, '[' + shifted + ']' if key == 'startposition' else shifted)
        if kind == 'side' and 'plane' in props:
            points = re.findall(r'\(([^)]+)\)', props['plane'])
            shifted = []
            for point in points:
                value = vector([float(number) for number in point.split()])
                shifted.append('(' + numbers([value[index] + delta[index] for index in range(3)]) + ')')
            set_property(data, 'plane', ' '.join(shifted))
        if kind == 'vertices_plus':
            for pair in data:
                if pair[0] == 'v' and isinstance(pair[1], str):
                    point = vector([float(value) for value in pair[1].split()])
                    pair[1] = numbers([point[index] + delta[index] for index in range(3)])


def edit(path, operations, expected_sha256):
    path, raw, pairs = load(path)
    if digest(raw) != expected_sha256:
        raise ValueError('Map changed. Read the map again before editing.')
    next_id = max((int(properties(data)['id']) for kind, data in walk(pairs) if 'id' in properties(data)), default=0) + 1
    def allocate():
        nonlocal next_id
        result = next_id
        next_id += 1
        return result
    added = []
    for operation in operations:
        action = operation['op']
        if action in ('add_box', 'add_entity', 'append'):
            if action == 'add_entity':
                props = operation['properties']
                if not props.get('classname'):
                    raise ValueError('An entity needs a classname')
                if any('\\' in str(value) for value in props.values()):
                    raise ValueError('Use forward slashes in entity paths; Hammer does not reliably round-trip backslashes.')
                data = [['id', str(allocate())]] + [[str(key), str(value)] for key, value in props.items() if key != 'id']
                if 'origin' in operation:
                    set_property(data, 'origin', numbers(vector(operation['origin'])))
                kind = 'entity'
                parent = pairs
            elif action == 'add_box':
                data = box(operation['min'], operation['max'], operation.get('material', 'tools/toolsnodraw'), allocate)
                kind = 'solid'
                parent = node(pairs, operation['parent_id'])[1] if 'parent_id' in operation else next(value for key, value in pairs if key == 'world')
            else:
                parent = node(pairs, operation['parent_id'])[1] if 'parent_id' in operation else pairs
                new_pairs = parse(operation['vmf'])
                for new_kind, new_data in new_pairs:
                    if not isinstance(new_data, list):
                        raise ValueError('append requires VMF blocks')
                    parent.append([new_kind, new_data])
                    if 'id' in properties(new_data):
                        added.append(int(properties(new_data)['id']))
                next_id = max((int(properties(data)['id']) for child_kind, data in walk(pairs) if 'id' in properties(data)), default=0) + 1
                continue
            parent.append([kind, data])
            added.append(int(properties(data)['id']))
        else:
            kind, data = node(pairs, operation['id'])
            if action == 'set':
                if 'id' in operation['properties']:
                    raise ValueError('Object ids cannot be changed with set')
                for key, value in operation['properties'].items():
                    set_property(data, key, value)
            elif action == 'remove':
                if kind == 'world':
                    raise ValueError('The world block cannot be removed')
                parent = next(parent for parent_kind, parent in walk(pairs) if any(value is data for key, value in parent))
                parent[:] = [[key, value] for key, value in parent if value is not data]
            elif action in ('move', 'duplicate'):
                if kind not in ('entity', 'solid'):
                    raise ValueError('move and duplicate accept entity or solid ids')
                if action == 'duplicate':
                    original = data
                    data = copy.deepcopy(data)
                    for child_kind, child_data in walk(data, kind):
                        if 'id' in properties(child_data):
                            set_property(child_data, 'id', str(allocate()))
                    parent = next(parent for parent_kind, parent in walk(pairs) if any(value is original for key, value in parent))
                    parent.append([kind, data])
                    added.append(int(properties(data)['id']))
                translate(data, operation['delta'])
            elif action == 'material':
                for child_kind, child_data in walk(data, kind):
                    if child_kind == 'side':
                        set_property(child_data, 'material', operation['material'])
            elif action == 'replace_node':
                replacement = operation['pairs']
                if properties(replacement).get('id') != str(operation['id']):
                    raise ValueError('replace_node must preserve the selected object id')
                data[:] = replacement
            else:
                raise ValueError(f'Unknown VMF operation: {action}')
    result = write(path, pairs, expected_sha256)
    result['added_ids'] = added
    return result
