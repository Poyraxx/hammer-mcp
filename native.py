import ctypes
import functools
import os
import re
import subprocess
import time
from ctypes import wintypes as w
from pathlib import Path

import psutil
import win32api
import win32con
import win32gui
import win32process


EXE = Path(os.environ.get('HAMMER_EXE', r'C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\bin\win64\hammerplusplus.exe')).resolve()
DLL = EXE.parent / 'hammerplusplus/bin/hammerplusplus_dll.dll'
GAME = EXE.parent.parent.parent / 'garrysmod'
U = ctypes.WinDLL('user32', use_last_error=True)
U.GetMenuStringW.argtypes = [w.HMENU, w.UINT, w.LPWSTR, ctypes.c_int, w.UINT]
U.GetMenuStringW.restype = ctypes.c_int
U.SendMessageTimeoutW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT, ctypes.POINTER(ctypes.c_size_t)]
U.SendMessageTimeoutW.restype = w.LPARAM
U.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
U.GetWindowTextW.restype = ctypes.c_int


class CopyData(ctypes.Structure):
    _fields_ = [('data', ctypes.c_size_t), ('size', w.DWORD), ('pointer', ctypes.c_void_p)]


def class_name(hwnd):
    try:
        return win32gui.GetClassName(hwnd)
    except win32gui.error as error:
        if error.winerror == 1400:
            return ''
        raise


def title(hwnd):
    buffer = ctypes.create_unicode_buffer(32768)
    U.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def send(hwnd, message, value=0, data=0):
    result = ctypes.c_size_t()
    if not U.SendMessageTimeoutW(hwnd, message, value, data, 2, 5000, ctypes.byref(result)):
        raise TimeoutError(f'Windows message {message} failed or timed out for {hwnd}: {ctypes.get_last_error()}')
    return result.value


def process_ids():
    result = set()
    for process in psutil.process_iter(['name', 'exe', 'pid']):
        try:
            if process.info['name'].lower() == EXE.name.lower() and process.info['exe'] and Path(process.info['exe']).resolve() == EXE:
                result.add(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            pass
    return result


def windows():
    pids = process_ids()
    result = []
    def collect(hwnd, unused):
        if win32process.GetWindowThreadProcessId(hwnd)[1] in pids:
            result.append(hwnd)
    win32gui.EnumWindows(collect, None)
    return result


def main():
    matches = [hwnd for hwnd in windows() if class_name(hwnd) == 'HammmerPlusPlus']
    if len(matches) != 1:
        raise RuntimeError(f'Expected one Hammer++ window, found {len(matches)}. Use hammer_start first.')
    return matches[0]


def describe(hwnd):
    kind = class_name(hwnd)
    text = title(hwnd)
    if kind in ('Edit', 'ComboBox', 'RichEdit20A', 'RichEdit20W', 'RICHEDIT50W'):
        size = min(send(hwnd, win32con.WM_GETTEXTLENGTH), 65535)
        buffer = ctypes.create_unicode_buffer(size + 1)
        send(hwnd, win32con.WM_GETTEXT, len(buffer), ctypes.addressof(buffer))
        text = buffer.value
    return {'hwnd': hwnd, 'id': win32gui.GetDlgCtrlID(hwnd), 'class': kind, 'text': text, 'visible': bool(win32gui.IsWindowVisible(hwnd)), 'enabled': bool(win32gui.IsWindowEnabled(hwnd))}


def children(hwnd):
    result = []
    win32gui.EnumChildWindows(hwnd, lambda child, unused: result.append(child), None)
    return result


def status():
    handles = windows()
    frames = [handle for handle in handles if class_name(handle) == 'HammmerPlusPlus']
    if not frames:
        return {'running': False, 'executable': str(EXE)}
    if len(frames) != 1:
        raise RuntimeError('Multiple Hammer++ processes are running.')
    hwnd = frames[0]
    mdi = next((child for child in children(hwnd) if class_name(child) == 'MDIClient'), None)
    documents = []
    active = send(mdi, 0x229) if mdi else 0
    if mdi:
        child = win32gui.GetWindow(mdi, win32con.GW_CHILD)
        while child:
            text = title(child)
            if text and text != 'Messages' and class_name(child) != 'ScrollBar':
                document = {**describe(child), 'active': child == active, 'modified': True if '*' in text else None}
                match = re.match(r'^(.+\.vmf)(?:\s*\*)?\s+-\s+', text, re.IGNORECASE)
                document['path'] = str(Path(match[1]).resolve()) if match else None
                documents.append(document)
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
    return {'running': True, 'pid': win32process.GetWindowThreadProcessId(hwnd)[1], 'window': describe(hwnd), 'documents': documents, 'dialogs': [describe(handle) for handle in handles if class_name(handle) == '#32770' and win32gui.IsWindowVisible(handle)]}


def start():
    if not process_ids():
        if not EXE.is_file():
            raise FileNotFoundError(EXE)
        subprocess.Popen([str(EXE)], cwd=EXE.parent, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if any(class_name(hwnd) == 'HammmerPlusPlus' for hwnd in windows()):
            return status()
        time.sleep(0.2)
    raise TimeoutError('Hammer++ did not create its main window within 45 seconds.')


def menu_items(menu, parents=()):
    result = []
    for index in range(win32gui.GetMenuItemCount(menu)):
        buffer = ctypes.create_unicode_buffer(1024)
        U.GetMenuStringW(menu, index, buffer, len(buffer), win32con.MF_BYPOSITION)
        label = buffer.value.replace('&', '').split('\t')[0]
        submenu = win32gui.GetSubMenu(menu, index)
        if submenu:
            result.extend(menu_items(submenu, parents + (label,)))
        elif label:
            state = win32gui.GetMenuState(menu, index, win32con.MF_BYPOSITION)
            result.append({'id': win32gui.GetMenuItemID(menu, index), 'name': ' > '.join(parents + (label,)), 'enabled': not bool(state & 3), 'checked': bool(state & 8)})
    return result


@functools.lru_cache(maxsize=1)
def catalog():
    module = win32api.LoadLibraryEx(str(DLL), 0, 34)
    result = {}
    try:
        for resource in win32api.EnumResourceNames(module, 4):
            menu = win32gui.LoadMenu(module, resource)
            try:
                for entry in menu_items(menu):
                    result.setdefault(entry['id'], {'id': entry['id'], 'name': entry['name']})
            finally:
                win32gui.DestroyMenu(menu)
    finally:
        win32api.FreeLibrary(module)
    return list(result.values())


def commands(query=''):
    live = {entry['id']: entry for entry in menu_items(win32gui.GetMenu(main()))}
    return [{**entry, 'available': entry['id'] in live, **({'enabled': live[entry['id']]['enabled'], 'checked': live[entry['id']]['checked']} if entry['id'] in live else {})} for entry in catalog() if query.casefold() in entry['name'].casefold() or query == str(entry['id'])]


def command(name):
    matches = [entry for entry in catalog() if str(entry['id']) == str(name) or entry['name'].casefold() == str(name).casefold()]
    if len(matches) != 1:
        raise ValueError('Use the exact command name or id returned by hammer_commands.')
    entry = matches[0]
    live = next((item for item in commands() if item['id'] == entry['id']), None)
    if live and live.get('enabled') is False:
        raise ValueError(f"Command is disabled: {entry['name']}")
    if not win32gui.IsWindowEnabled(main()):
        raise RuntimeError('A modal dialog is open. Inspect hammer_controls and finish it first.')
    win32gui.PostMessage(main(), win32con.WM_COMMAND, entry['id'], 0)
    time.sleep(0.15)
    return {'dispatched': entry, 'status': status()}


def validate_handle(hwnd):
    if not win32gui.IsWindow(hwnd) or win32process.GetWindowThreadProcessId(hwnd)[1] not in process_ids():
        raise ValueError('The window does not belong to this Hammer++ installation.')
    return hwnd


def controls(hwnd=None):
    root = validate_handle(hwnd) if hwnd else main()
    roots = [root] if hwnd else [root] + [handle for handle in windows() if handle != root and win32gui.IsWindowVisible(handle)]
    result = []
    seen = set()
    for parent in roots:
        for child in [parent] + children(parent):
            if child in seen or not win32gui.IsWindowVisible(child):
                continue
            seen.add(child)
            item = describe(child)
            item['parent'] = win32gui.GetParent(child)
            if item['class'] == 'Button':
                item['checked'] = send(child, win32con.BM_GETCHECK)
            elif item['class'] in ('ComboBox', 'ListBox'):
                combo = item['class'] == 'ComboBox'
                count = send(child, 0x146 if combo else 0x18B)
                if count < 10000:
                    values = []
                    for index in range(min(count, 100)):
                        size = send(child, 0x149 if combo else 0x18A, index)
                        if size < 65536:
                            text = ctypes.create_unicode_buffer(size + 1)
                            send(child, 0x148 if combo else 0x189, index, ctypes.addressof(text))
                            values.append(text.value)
                    item['items'] = values
                    item['item_count'] = count
                    item['selected'] = send(child, 0x147 if combo else 0x188)
            elif item['class'] == 'SysTabControl32':
                item['item_count'] = send(child, 0x1304)
                item['selected'] = send(child, 0x130B)
            result.append(item)
    return result


def control(hwnd, action, value=None):
    validate_handle(hwnd)
    if not win32gui.IsWindowEnabled(hwnd):
        raise ValueError('Control is disabled.')
    kind = class_name(hwnd)
    parent = win32gui.GetParent(hwnd)
    cid = win32gui.GetDlgCtrlID(hwnd)
    if action == 'text':
        if kind not in ('Edit', 'ComboBox', 'RichEdit20A', 'RichEdit20W', 'RICHEDIT50W'):
            raise ValueError(f'Control does not accept text: {kind}')
        text = ctypes.create_unicode_buffer(str(value))
        if not send(hwnd, win32con.WM_SETTEXT, 0, ctypes.addressof(text)):
            raise RuntimeError('Control rejected its text.')
        win32gui.PostMessage(parent, win32con.WM_COMMAND, cid | (win32con.EN_CHANGE << 16), hwnd)
    elif action in ('press', 'check'):
        if kind != 'Button':
            raise ValueError('press and check require a Button control.')
        if action == 'press' or bool(send(hwnd, win32con.BM_GETCHECK)) != bool(value):
            win32gui.PostMessage(hwnd, win32con.BM_CLICK, 0, 0)
    elif action == 'select':
        if kind == 'SysTabControl32':
            index = int(value)
            if not 0 <= index < send(hwnd, 0x1304):
                raise ValueError('Tab index is out of range.')
            send(hwnd, 0x1330, index)
            if send(hwnd, 0x130B) != index:
                raise RuntimeError('This tab control did not accept the requested selection.')
            return {'status': status(), 'controls': controls(parent)}
        if kind not in ('ComboBox', 'ListBox'):
            raise ValueError('select requires a ComboBox or ListBox control.')
        combo = kind == 'ComboBox'
        index = int(value)
        count = send(hwnd, 0x146 if combo else 0x18B)
        if not 0 <= index < count:
            raise ValueError('Selection index is out of range.')
        send(hwnd, 0x14E if combo else 0x186, index)
        win32gui.PostMessage(parent, win32con.WM_COMMAND, cid | (1 << 16), hwnd)
    else:
        raise ValueError('Supported actions: text, press, check, select.')
    time.sleep(0.15)
    return {'status': status(), 'controls': controls(parent) if win32gui.IsWindow(parent) else []}


def activate(hwnd):
    validate_handle(hwnd)
    parent = win32gui.GetParent(hwnd)
    if not parent or class_name(parent) != 'MDIClient':
        raise ValueError('Use a document hwnd returned by hammer_status.')
    send(parent, 0x222, hwnd)
    return status()


def wait_ready(timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = status()
        if state.get('running') and state['window']['enabled'] and not state['dialogs']:
            return state
        if state.get('dialogs') and any(not any(class_name(child) == 'msctls_progress32' for child in children(dialog['hwnd'])) and dialog['text'] != 'Loading File' for dialog in state['dialogs']):
            raise RuntimeError(f'Hammer++ is waiting on a dialog: {state["dialogs"]}')
        time.sleep(0.1)
    raise TimeoutError('Hammer++ did not finish the requested operation.')


def active_document():
    state = status()
    return next((document for document in state.get('documents', []) if document['active']), None)


def file_dialog(path, command_id):
    before = set(windows())
    command(command_id)
    deadline = time.monotonic() + 15
    dialog = None
    while time.monotonic() < deadline:
        candidates = [handle for handle in windows() if handle not in before and class_name(handle) == '#32770' and win32gui.IsWindowVisible(handle)]
        for handle in candidates:
            edits = [child for child in children(handle) if class_name(child) == 'Edit' and win32gui.GetDlgCtrlID(child) == 1148]
            if len(edits) == 1:
                dialog, edit = handle, edits[0]
                break
        if dialog:
            break
        time.sleep(0.1)
    if not dialog:
        raise TimeoutError('The expected Windows file dialog did not appear. Inspect hammer_controls.')
    control(edit, 'text', str(path))
    button = win32gui.GetDlgItem(dialog, 1)
    if not button:
        raise RuntimeError('The file dialog has no accept button.')
    win32gui.PostMessage(button, win32con.BM_CLICK, 0, 0)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if not win32gui.IsWindow(dialog):
            state = status()
            if state['window']['enabled']:
                return state
        time.sleep(0.1)
    raise TimeoutError('The file operation did not complete. Inspect hammer_controls.')


def open_map(path):
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != '.vmf':
        raise ValueError('Expected a .vmf map')
    start()
    existing = [document for document in status()['documents'] if document['path'] and Path(document['path']) == path]
    if existing:
        return activate(existing[0]['hwnd'])
    state = file_dialog(path, 57601)
    if not any(document['path'] and Path(document['path']) == path for document in state['documents']):
        raise RuntimeError('The file dialog closed but Hammer++ did not report the requested map.')
    return state


def save(path=None):
    document = active_document()
    if not document:
        raise RuntimeError('No map is active')
    if path:
        path = Path(path).resolve()
        if path.suffix.lower() != '.vmf':
            raise ValueError('Expected a .vmf map')
        if path.exists() and (not document['path'] or Path(document['path']) != path):
            raise FileExistsError('Save As refuses to overwrite another existing map')
        if not document['path'] or Path(document['path']) != path:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_dialog(path, 57604)
        else:
            command(57603)
    elif document['path']:
        command(57603)
    else:
        raise ValueError('An untitled map needs an explicit save path')
    state = wait_ready()
    current = active_document()
    if not current or current['modified'] or not current['path'] or not Path(current['path']).is_file():
        raise RuntimeError('Hammer++ did not confirm a saved map')
    return {'path': current['path'], 'status': state}


def reload_map(path):
    path = Path(path).resolve(strict=True)
    documents = [document for document in status()['documents'] if document['path'] and Path(document['path']) == path]
    if documents:
        if documents[0]['modified']:
            raise RuntimeError('The editor has unsaved changes. Save the map before reloading.')
        activate(documents[0]['hwnd'])
        command(57602)
        wait_ready()
    return open_map(path)


def shell_message(text):
    candidates = [hwnd for hwnd in windows() if class_name(hwnd) == 'Worldcraft_ShellMessageWnd']
    if len(candidates) != 1:
        raise RuntimeError('Hammer++ shell message window is unavailable')
    raw = text.encode('mbcs', errors='strict')
    if b'\x00' in raw or len(raw) > 8191:
        raise ValueError('Shell message contains a NUL or exceeds 8191 bytes')
    payload = ctypes.create_string_buffer(raw + b'\x00')
    data = CopyData(0, len(payload), ctypes.addressof(payload))
    return bool(send(candidates[0], win32con.WM_COPYDATA, 0, ctypes.addressof(data)))


def live_entities(operations):
    if not active_document() or not win32gui.IsWindowEnabled(main()):
        raise RuntimeError('A map must be active without a modal dialog')
    def token(value):
        text = str(value)
        if not text or len(text.encode('mbcs')) > 400 or any(character in text for character in '\\"\r\n\x00'):
            raise ValueError('Shell values must be nonempty, at most 400 bytes, and contain no backslash, quote, newline or NUL; use forward slashes in asset paths')
        return '"' + text + '"'
    messages = []
    for operation in operations:
        action = operation['op']
        classname = operation['classname']
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,126}', classname):
            raise ValueError('Invalid entity classname')
        from vmf import vector, numbers
        origin = numbers(vector(operation['origin']))
        if action in ('create', 'delete'):
            messages.append(f'entity_{action} {classname} {origin}')
        elif action == 'set':
            properties = dict(operation['properties'])
            if 'classname' in properties:
                raise ValueError('Change classname through VMF editing, not the origin-based shell protocol')
            for coordinate in ('origin', 'angles'):
                if coordinate in properties:
                    properties[coordinate] = numbers(vector([float(value) for value in str(properties[coordinate]).split()]))
            for key in sorted(properties, key=lambda key: key == 'origin'):
                value = properties[key]
                messages.append(f'entity_set_keyvalue {classname} {origin} {token(key)} {token(value)}')
        elif action == 'rotate':
            messages.append(f'entity_rotate_incremental {classname} {origin} {numbers(vector(operation["angles"]))}')
        else:
            raise ValueError('Live entity actions: create, delete, set, rotate')
    if not shell_message('session_begin'):
        raise RuntimeError('Hammer++ refused to begin the native edit session')
    completed = []
    try:
        for message in messages:
            if not shell_message(message):
                return {'completed': completed, 'failed': message, 'status': status()}
            completed.append(message)
    finally:
        if not shell_message('session_end'):
            raise RuntimeError('Hammer++ did not close its native edit session')
    return {'completed': completed, 'status': status()}
