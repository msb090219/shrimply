"""Login entries use quiet startup for source and packaged builds."""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from shrimply import autostart


@pytest.mark.parametrize('frozen', [False, True])
def test_login_command_uses_background(monkeypatch, frozen):
    monkeypatch.setattr(sys, 'frozen', frozen, raising=False)
    monkeypatch.setattr(sys, 'executable', r'C:\Program Files\Shrimply\shrimply.exe' if frozen else r'C:\Python\python.exe')
    command = autostart._command()
    assert command.endswith(' --background')
    assert command.startswith('"')
    if not frozen:
        assert str(Path(autostart.__file__).resolve().parent.parent / 'main.py') in command


def test_enabled_login_entry_writes_background_command(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    registry = Mock()
    registry.OpenKey.return_value.__enter__ = Mock(return_value='key')
    registry.OpenKey.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(autostart, 'winreg', registry)
    autostart.set_enabled(True)
    assert registry.SetValueEx.call_args.args[-1].endswith(' --background')
    registry.DeleteValue.assert_called_once_with('key', 'Unshrimp')


@pytest.mark.parametrize("frozen", [False, True])
def test_mac_login_entry_roundtrip_preserves_paths_and_disables_cleanly(tmp_path, monkeypatch, frozen):
    import plistlib
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    executable = (tmp_path / "App Folder/Shrimply.app/Contents/MacOS/Shrimply"
                  if frozen else tmp_path / "Source Folder/.venv/bin/python")
    monkeypatch.setattr(sys, "executable", str(executable))
    path = tmp_path / "LaunchAgents/com.msb090219.shrimply.plist"
    monkeypatch.setattr(autostart, "_mac_path", lambda: path)
    registry = Mock()
    monkeypatch.setattr(autostart, "winreg", registry)
    assert not autostart.is_enabled()
    autostart.set_enabled(True)
    assert autostart.is_enabled()
    entry = plistlib.loads(path.read_bytes())
    expected = (["/usr/bin/open", "-g", str(executable.parents[2]), "--args", "--background"]
                if frozen else [str(executable), str(Path(autostart.__file__).resolve().parent.parent / "main.py"), "--background"])
    assert entry["ProgramArguments"] == expected
    assert entry["LimitLoadToSessionType"] == "Aqua"
    autostart.set_enabled(False)
    autostart.set_enabled(False)
    assert not path.exists() and not autostart.is_enabled()
    registry.OpenKey.assert_not_called()


def test_old_login_entry_is_replaced_and_removed(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    registry = Mock()
    registry.OpenKey.return_value.__enter__ = Mock(return_value='key')
    registry.OpenKey.return_value.__exit__ = Mock(return_value=False)
    def query(_key, name):
        if name == 'Unshrimp':
            return 'old command', 1
        raise OSError('missing')
    registry.QueryValueEx.side_effect = query
    monkeypatch.setattr(autostart, 'winreg', registry)

    assert autostart.is_enabled()
    autostart.set_enabled(True)
    assert registry.SetValueEx.call_args.args[1] == 'Shrimply'
    registry.DeleteValue.assert_called_with('key', 'Unshrimp')
    registry.DeleteValue.reset_mock()
    autostart.set_enabled(False)
    assert [call.args[1] for call in registry.DeleteValue.call_args_list] == ['Shrimply', 'Unshrimp']


@pytest.mark.parametrize("enable", [False, True])
def test_mac_rename_replaces_or_disables_old_login_entry(tmp_path, monkeypatch, enable):
    import plistlib
    monkeypatch.setattr(sys, "platform", "darwin")
    path = tmp_path / "LaunchAgents/com.msb090219.shrimply.plist"
    monkeypatch.setattr(autostart, "_mac_path", lambda: path)
    old = autostart._legacy_mac_path()
    old.parent.mkdir(parents=True)
    old.write_bytes(plistlib.dumps({"Label": autostart.LEGACY_MAC_LABEL,
                                  "RunAtLoad": True, "ProgramArguments": ["old app"]}))
    assert autostart.is_enabled()
    autostart.set_enabled(enable)
    assert autostart.is_enabled() is enable
    assert not old.exists()
    assert path.exists() is enable
    if enable:
        assert plistlib.loads(path.read_bytes())["Label"] == autostart.MAC_LABEL


def test_failed_mac_login_replacement_preserves_old_entry(tmp_path, monkeypatch):
    import plistlib
    monkeypatch.setattr(sys, "platform", "darwin")
    path = tmp_path / "com.msb090219.shrimply.plist"
    monkeypatch.setattr(autostart, "_mac_path", lambda: path)
    old = autostart._legacy_mac_path()
    original = plistlib.dumps({"Label": autostart.LEGACY_MAC_LABEL, "RunAtLoad": True})
    old.write_bytes(original)
    monkeypatch.setattr(autostart.os, "replace", Mock(side_effect=OSError("Disk full")))
    with pytest.raises(OSError, match="Disk full"):
        autostart.set_enabled(True)
    assert old.read_bytes() == original
    assert not path.exists()
    assert autostart.is_enabled()
