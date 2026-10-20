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
    registry = Mock()
    registry.OpenKey.return_value.__enter__ = Mock(return_value='key')
    registry.OpenKey.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(autostart, 'winreg', registry)
    autostart.set_enabled(True)
    assert registry.SetValueEx.call_args.args[-1].endswith(' --background')
    registry.DeleteValue.assert_called_once_with('key', 'Unshrimp')


def test_old_login_entry_is_replaced_and_removed(monkeypatch):
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
