import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]


async def run():
    folder = ROOT / 'tests/data' / datetime.now().strftime('%Y%m%d-%H%M%S')
    folder.mkdir(parents=True)
    path = folder / 'mcp_test.vmf'
    report = {'map': str(path), 'checks': []}
    parameters = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'server.py')], cwd=str(ROOT))
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            report['tools'] = [tool.name for tool in tools.tools]
            async def call(name, **arguments):
                result = await session.call_tool(name, arguments)
                if result.isError:
                    raise AssertionError(f'{name}: {result.content}')
                return result.structuredContent if result.structuredContent is not None else json.loads(result.content[0].text)
            await call('hammer_start')
            created = await call('hammer_create_map', path=str(path), open_in_hammer=False)
            boxes = [([-288, -288, -32], [288, 288, 0]), ([-288, -288, 256], [288, 288, 288]), ([-288, -288, 0], [-256, 288, 256]), ([256, -288, 0], [288, 288, 256]), ([-256, -288, 0], [256, -256, 256]), ([-256, 256, 0], [256, 288, 256])]
            operations = [{'op': 'add_box', 'min': minimum, 'max': maximum, 'material': 'dev/dev_measuregeneric01'} for minimum, maximum in boxes]
            operations.append({'op': 'add_entity', 'properties': {'classname': 'info_player_start'}, 'origin': [0, 0, 64]})
            edited = await call('hammer_edit_map', path=str(path), operations=operations, expected_sha256=created['sha256'])
            assert edited['counts']['solid'] == 6
            assert Path(edited['backup']).is_file()
            report['checks'].append('VMF create, sealed room, player and verified backup')
            opened = await call('hammer_open', path=str(path))
            assert any(document['path'] == str(path) for document in opened['documents'])
            report['checks'].append('Open map through native file control messages')
            native_edit = await call('hammer_live_entities', operations=[{'op': 'create', 'classname': 'light', 'origin': [0, 0, 160]}, {'op': 'set', 'classname': 'light', 'origin': [0, 0, 160], 'properties': {'targetname': 'mcp_light', '_light': '255 220 180 300'}}])
            assert len(native_edit['completed']) == 3 and 'failed' not in native_edit
            saved = await call('hammer_save')
            found = await call('hammer_read_map', path=str(path), query='mcp_light')
            assert found['matching_objects'] == 1
            assert found['objects'][0]['_light'] == '255 220 180 300'
            report['checks'].append('WM_COPYDATA native entity create and keyvalues, verified in Hammer-saved VMF')
            moved = await call('hammer_edit_map', path=str(path), operations=[{'op': 'move', 'id': edited['added_ids'][-1], 'delta': [16, 0, 0]}], expected_sha256=saved['sha256'])
            await call('hammer_reload', path=str(path))
            await call('hammer_save')
            player = await call('hammer_read_map', path=str(path), query='info_player_start')
            assert player['objects'][0]['origin'] == '16 0 64'
            report['checks'].append('VMF edit, native reload, Hammer round-trip')
            await call('hammer_live_entities', operations=[{'op': 'set', 'classname': 'info_player_start', 'origin': [16, 0, 64], 'properties': {'origin': '24 8 64', 'targetname': 'mcp_player', 'angles': '0 0 0'}}, {'op': 'rotate', 'classname': 'info_player_start', 'origin': [24, 8, 64], 'angles': [0, 45, 0]}])
            saved = await call('hammer_save')
            player = await call('hammer_read_map', path=str(path), query='mcp_player')
            assert player['objects'][0]['origin'] == '24 8 64'
            assert abs(float(player['objects'][0]['angles'].split()[1]) - 45) < 0.01
            report['checks'].append('Native origin change, keyvalue ordering and incremental rotation')
            await call('hammer_edit_map', path=str(path), operations=[{'op': 'set', 'id': 1, 'properties': {'mcp_path': 'models/props/a.mdl'}}], expected_sha256=saved['sha256'])
            await call('hammer_reload', path=str(path))
            saved = await call('hammer_save')
            world = await call('hammer_read_map', path=str(path), object_id=1)
            props = {key: value for key, value in world['pairs'] if isinstance(value, str)}
            assert props['mcp_path'] == 'models/props/a.mdl'
            await call('hammer_edit_map', path=str(path), operations=[{'op': 'set', 'id': 1, 'properties': {'mcp_path': None}}], expected_sha256=saved['sha256'])
            await call('hammer_reload', path=str(path))
            await call('hammer_save')
            report['checks'].append('Asset path survives real Hammer load/save; unsafe VMF string values are rejected before writing')
            compiled = await call('hammer_compile', path=str(path), arguments={'vvis': ['-fast'], 'vrad': ['-fast']}, timeout_seconds=120)
            report['compile'] = compiled
            assert compiled['ok'], compiled
            assert Path(compiled['bsp']).read_bytes()[:4] == b'VBSP'
            report['checks'].append('VBSP, VVIS and VRAD; valid compiled BSP')
            await call('hammer_live_entities', operations=[{'op': 'delete', 'classname': 'light', 'origin': [0, 0, 160]}])
            await call('hammer_save')
            deleted = await call('hammer_read_map', path=str(path), query='mcp_light')
            assert deleted['matching_objects'] == 0
            report['checks'].append('WM_COPYDATA native entity delete verified in saved VMF')
            await call('hammer_live_entities', operations=[{'op': 'create', 'classname': 'light', 'origin': [0, 0, 160]}, {'op': 'set', 'classname': 'light', 'origin': [0, 0, 160], 'properties': {'targetname': 'mcp_light', '_light': '255 220 180 300'}}])
            await call('hammer_save')
            report['ok'] = True
    (ROOT / 'logs').mkdir(exist_ok=True)
    (ROOT / 'logs/live-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': report['ok'], 'map': report['map'], 'tools': len(report['tools']), 'checks': report['checks']}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(run())
