import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch, MagicMock

from ai_help import core, shell


class AssetsTests(unittest.TestCase):
    def test_ico_contains_all_rgba_png_sizes_with_valid_crc(self):
        data = shell.ICON.read_bytes()
        self.assertEqual(struct.unpack_from('<HHH', data), (0, 1, 7))
        for index, size in enumerate((16, 24, 32, 48, 64, 128, 256)):
            w, h, palette, reserved, planes, bits, length, offset = struct.unpack_from('<BBBBHHII', data, 6+16*index)
            self.assertEqual((w or 256, h or 256, planes, bits), (size, size, 1, 32))
            png = data[offset:offset+length]
            self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
            position, compressed, kinds = 8, bytearray(), []
            while position < len(png):
                length, = struct.unpack_from('>I', png, position)
                kind = png[position+4:position+8]
                payload = png[position+8:position+8+length]
                crc, = struct.unpack_from('>I', png, position+8+length)
                self.assertEqual(crc, zlib.crc32(kind+payload))
                kinds.append(kind)
                if kind == b'IHDR':
                    self.assertEqual(struct.unpack('>IIBBBBB', payload), (size, size, 8, 6, 0, 0, 0))
                if kind == b'IDAT':
                    compressed.extend(payload)
                position += 12+length
            self.assertEqual(kinds, [b'IHDR', b'IDAT', b'IEND'])
            self.assertEqual(len(zlib.decompress(compressed)), size*(1+size*4))

    def test_icon_fallback_and_refresh_all_registered_items(self):
        self.assertEqual(shell.menu_icon(), str(shell.ICON))
        with patch.object(shell, 'ICON', Path('missing-cat-icon.ico')):
            self.assertTrue(shell.menu_icon().endswith('pythonw.exe'))
        import winreg
        registry = MagicMock()
        with patch.object(winreg, 'OpenKey', registry.OpenKey), patch.object(winreg, 'CreateKey', registry.CreateKey), \
             patch.object(winreg, 'SetValueEx', registry.SetValueEx), patch.object(shell.ctypes.windll.shell32, 'SHChangeNotify'):
            shell.refresh_menu('团子')
        icons = [call for call in registry.SetValueEx.call_args_list if call.args[1] == 'Icon']
        self.assertEqual(len(icons), 4)
        self.assertTrue(all(call.args[-1] == str(shell.ICON) for call in icons))

    def test_old_config_gets_medium_size_default(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'config.json'
            config.write_text('{"nickname": "团子"}', encoding='utf-8')
            with patch.object(core, 'CONFIG', config):
                self.assertEqual(core.load_config()['pet_size'], '中')
