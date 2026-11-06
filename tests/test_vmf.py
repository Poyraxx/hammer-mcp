import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vmf


class MapTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'test.vmf'
        self.created = vmf.create(self.path)

    def test_roundtrip_preserves_duplicate_connections_and_paths(self):
        pairs = [['entity', [['id', '2'], ['classname', 'logic_relay'], ['model', r'models\props\a.mdl'], ['connections', [['OnTrigger', 'a,Enable,,0,-1'], ['OnTrigger', 'b,Enable,,1,-1']]]]]]
        self.assertEqual(vmf.parse(vmf.dump(pairs)), pairs)

    def test_embedded_quote_is_rejected_before_writing(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            vmf.edit(self.path, [{'op': 'set', 'id': 1, 'properties': {'message': 'a "b" c'}}], self.created['sha256'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_unsafe_backslash_edit_is_rejected_without_changing_the_map(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            vmf.edit(self.path, [{'op': 'set', 'id': 1, 'properties': {'model': r'models\props\a.mdl'}}], self.created['sha256'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_brush_entity_move_and_verified_backup(self):
        original = self.path.read_bytes()
        result = vmf.edit(self.path, [{'op': 'add_box', 'min': [-32, -32, -16], 'max': [32, 32, 0]}, {'op': 'add_entity', 'properties': {'classname': 'info_player_start'}, 'origin': [0, 0, 64]}], self.created['sha256'])
        self.assertEqual(Path(result['backup']).read_bytes(), original)
        self.assertEqual(result['counts']['side'], 6)
        moved = vmf.edit(self.path, [{'op': 'move', 'id': result['added_ids'][1], 'delta': [16, -8, 4]}], result['sha256'])
        self.assertEqual(vmf.read(self.path, result['added_ids'][1])['pairs'][-1], ['origin', '16 -8 68'])
        self.assertEqual(moved['counts']['entity'], 1)

    def test_stale_digest_does_not_change_the_map(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            vmf.edit(self.path, [{'op': 'set', 'id': 1, 'properties': {'skyname': 'other'}}], '0' * 64)
        self.assertEqual(self.path.read_bytes(), before)

    def test_existing_turkish_encoding_is_retained(self):
        source = self.path.read_text(encoding='utf-8').replace('sky_day01_01', 'çağrı')
        self.path.write_bytes(source.encode('cp1254'))
        before = self.path.read_bytes()
        current = vmf.read(self.path)
        vmf.edit(self.path, [{'op': 'set', 'id': 1, 'properties': {'mapversion': '2'}}], current['sha256'])
        self.assertIn('çağrı'.encode('cp1254'), self.path.read_bytes())
        self.assertEqual(self.path.read_bytes(), before.replace(b'"id" "1"\n\t"mapversion" "1"', b'"id" "1"\n\t"mapversion" "2"', 1))

    def test_duplicate_id_is_rejected_without_writing(self):
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            vmf.edit(self.path, [{'op': 'append', 'vmf': 'entity { "id" "1" "classname" "light" }'}], self.created['sha256'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_brush_and_infinite_coordinates_are_rejected(self):
        for minimum, maximum in [([0, 0, 0], [0, 1, 1]), ([0, 0, 0], [float('inf'), 1, 1])]:
            with self.subTest(maximum=maximum):
                with self.assertRaises(ValueError):
                    vmf.edit(self.path, [{'op': 'add_box', 'min': minimum, 'max': maximum}], self.created['sha256'])

    def test_new_map_never_overwrites(self):
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            vmf.create(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_unclosed_block_is_rejected(self):
        with self.assertRaises(ValueError):
            vmf.parse('world { "id" "1"')

    def test_move_preserves_hammer_vertex_positions(self):
        pairs = [['solid', [['id', '2'], ['vertices_plus', [['v', '1 2 3'], ['v', '4 5 6']]]]]]
        vmf.translate(pairs, [10, 20, 30])
        self.assertEqual(pairs[0][1][1][1], [['v', '11 22 33'], ['v', '14 25 36']])


if __name__ == '__main__':
    unittest.main()
