import asyncio
import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import psutil
from mcp.server.fastmcp import FastMCP

import native
import vmf


MCP = FastMCP('Hammer', log_level='WARNING', instructions='Control Hammer++ through native Windows messages and VMF data. No mouse, screenshots, or keyboard injection. Read hammer_status and hammer_commands before editor actions. Save the active map before reading/editing its file. VMF edits require the current sha256 and make verified backups. Native entity operations identify entities by classname plus origin, not targetname or id. Native batches can partially complete; inspect completed and failed. A missing modified indicator means unknown, not clean. File reload never dismisses save prompts. Use hammer_controls to inspect and resolve dialogs. Use VMF replace_node/append for geometry or data not covered by convenience operations.')
LOCK = threading.RLock()
ROOT = Path(__file__).resolve().parent


@MCP.tool(description='Read Hammer++ process, active map paths, document handles and open dialogs. modified=null means the title does not expose unsaved state.')
def hammer_status() -> dict[str, Any]:
    return native.status()


@MCP.tool(description='Start the installed Hammer++ or connect to its existing process.')
def hammer_start() -> dict[str, Any]:
    with LOCK:
        return native.start()


@MCP.tool(description='Search commands extracted from this Hammer++ DLL. Use an exact returned id or name with hammer_command. available/enabled describe the current menu.')
def hammer_commands(query: str = '') -> list[dict[str, Any]]:
    return native.commands(query)


@MCP.tool(description='Dispatch an exact Hammer menu command through WM_COMMAND. Returns dispatched, not proof of the requested edit. Inspect status, dialogs or saved VMF to verify.')
def hammer_command(command: str) -> dict[str, Any]:
    with LOCK:
        return native.command(command)


@MCP.tool(description='Read actual Hammer control handles, ids, text, checkbox states and combo/list choices. Optional hwnd restricts the read to one dialog or pane. No screenshots.')
def hammer_controls(hwnd: int | None = None) -> list[dict[str, Any]]:
    return native.controls(hwnd)


@MCP.tool(description='Send a native control action to a Hammer-owned hwnd: text, press, check, select. select uses a zero-based combo/list/tab index. No mouse or keyboard events.')
def hammer_control(hwnd: int, action: str, value: Any = None) -> dict[str, Any]:
    with LOCK:
        return native.control(hwnd, action, value)


@MCP.tool(description='Activate a document hwnd returned by hammer_status through the MDI message interface.')
def hammer_activate(hwnd: int) -> dict[str, Any]:
    with LOCK:
        return native.activate(hwnd)


@MCP.tool(description='Open an existing VMF in Hammer++ or activate it if already open. The Windows file dialog is driven using control messages.')
def hammer_open(path: str) -> dict[str, Any]:
    with LOCK:
        return native.open_map(path)


@MCP.tool(description='Save the active map using Hammer itself. An untitled map requires path. Save As refuses to overwrite an unrelated existing file.')
def hammer_save(path: str | None = None) -> dict[str, Any]:
    with LOCK:
        result = native.save(path)
        return {**vmf.read(result['path'], limit=1), 'status': result['status']}


@MCP.tool(description='Close and reopen an on-disk VMF. Hammer save prompts remain open instead of discarding unsaved work. Use hammer_controls if a prompt blocks the operation.')
def hammer_reload(path: str) -> dict[str, Any]:
    with LOCK:
        return native.reload_map(path)


@MCP.tool(description='Create a new VMF without overwriting an existing file. Optionally open it in Hammer++.')
def hammer_create_map(path: str, open_in_hammer: bool = True) -> dict[str, Any]:
    with LOCK:
        result = vmf.create(path)
        if open_in_hammer:
            result['status'] = native.open_map(path)
        return result


@MCP.tool(description='Read VMF object ids/properties and sha256. object_id returns the full ordered key/value pairs for that object, preserving duplicate connections and unknown Hammer++ blocks. query filters object text; results are paginated.')
def hammer_read_map(path: str, object_id: int | None = None, query: str = '', offset: int = 0, limit: int = 100, full: bool = False) -> dict[str, Any]:
    return vmf.read(path, object_id, query, offset, limit, full)


@MCP.tool(description='Replace a saved map with complete VMF text. Validates syntax, world block, ids, brush side count and serialization before writing; requires current expected_sha256 and creates a verified backup. This supports cameras, displacements, I/O, instances, visgroups and unknown Hammer++ blocks through their original VMF representation. Save the editor before reading/editing; reload separately.')
def hammer_write_map(path: str, text: str, expected_sha256: str) -> dict[str, Any]:
    with LOCK:
        return vmf.write(path, vmf.parse(text), expected_sha256)


@MCP.tool(description='Edit VMF with optimistic sha256 verification and a verified backup. Operations: add_box(min,max,material,parent_id optional), add_entity(properties,origin optional), set(id,properties; null removes a property), remove(id), move/duplicate(id,delta), material(id,material), replace_node(id,pairs), append(vmf,parent_id optional). append retains supplied ids and rejects collisions. Save the editor map before reading its sha256. Changes affect disk; call hammer_reload to show them.')
def hammer_edit_map(path: str, operations: list[dict[str, Any]], expected_sha256: str) -> dict[str, Any]:
    with LOCK:
        return vmf.edit(path, operations, expected_sha256)


@MCP.tool(description='Edit the currently active map live through the reverse-engineered WM_COPYDATA shell protocol. Operations use op=create/delete/set/rotate, classname and origin[3]; set also needs properties; rotate needs angles[3]. Classname plus origin must uniquely identify the entity. Origin key changes move it. Batches report partial completion. Save and read the VMF to verify.')
def hammer_live_entities(operations: list[dict[str, Any]]) -> dict[str, Any]:
    with LOCK:
        return native.live_entities(operations)


@MCP.tool(description='Compile a saved VMF directly with the installed vbsp/vvis/vrad tools. Returns exit codes and persistent log paths. Does not launch Garry\'s Mod. stages defaults to all three. arguments optionally supplies each stage\'s exact flags, such as {"vvis":["-fast"],"vrad":["-fast"]}.')
def hammer_compile(path: str, stages: list[str] | None = None, arguments: dict[str, list[str]] | None = None, timeout_seconds: int = 300) -> dict[str, Any]:
    with LOCK:
        map_path, raw, data = vmf.load(path)
        vmf.validate(data)
        chosen = stages if stages is not None else ['vbsp', 'vvis', 'vrad']
        if not chosen or len(set(chosen)) != len(chosen) or any(stage not in ('vbsp', 'vvis', 'vrad') for stage in chosen):
            raise ValueError('Choose each of vbsp, vvis and vrad at most once')
        if chosen != sorted(chosen, key=['vbsp', 'vvis', 'vrad'].index):
            raise ValueError('Compiler stages must follow vbsp, vvis, vrad order')
        if not 1 <= timeout_seconds <= 3600:
            raise ValueError('timeout_seconds must be between 1 and 3600')
        logs = ROOT / 'logs'
        logs.mkdir(exist_ok=True)
        runs = []
        for stage in chosen:
            executable = native.EXE.parent / (stage + '.exe')
            flags = (arguments or {}).get(stage, [])
            if not isinstance(flags, list) or any(not isinstance(flag, str) or '\x00' in flag for flag in flags):
                raise ValueError('Compiler flags must be strings without NULs')
            command = [str(executable), '-game', str(native.GAME), *flags, str(map_path if stage == 'vbsp' else map_path.with_suffix(''))]
            process = subprocess.Popen(command, cwd=executable.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            timed_out = False
            try:
                output, unused = process.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                parent = psutil.Process(process.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.kill()
                    except psutil.NoSuchProcess:
                        pass
                process.kill()
                output, unused = process.communicate()
            log = logs / f'{map_path.stem}.{stage}.{process.pid}.log'
            log.write_bytes(output)
            text = output.decode('utf-8', errors='replace')
            leaked = '**** leaked ****' in text.casefold()
            runs.append({'stage': stage, 'command': command, 'exit_code': process.returncode, 'timed_out': timed_out, 'leaked': leaked, 'log': str(log), 'tail': text[-6000:]})
            if timed_out or process.returncode != 0 or leaked:
                return {'ok': False, 'stages': runs}
        bsp = map_path.with_suffix('.bsp')
        return {'ok': bsp.is_file() and bsp.read_bytes()[:4] == b'VBSP', 'bsp': str(bsp), 'stages': runs}


if __name__ == '__main__':
    if len(sys.argv) == 1:
        MCP.run(transport='stdio')
    elif sys.argv[1] == 'list':
        async def listing():
            tools = await MCP.list_tools()
            print(json.dumps([tool.model_dump(exclude_none=True) for tool in tools], ensure_ascii=False))
        asyncio.run(listing())
    else:
        async def call():
            arguments = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
            result = await MCP.call_tool(sys.argv[1], arguments)
            if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
                result = result[1]
            print(json.dumps(result, ensure_ascii=False, default=lambda value: value.model_dump(exclude_none=True)))
        asyncio.run(call())
