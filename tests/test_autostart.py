"""Login entries use quiet startup for source and packaged builds."""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from unshrimp import autostart


@pytest.mark.parametrize('frozen', [False, True])
def test_login_command_uses_background(monkeypatch, frozen):
    monkeypatch.setattr(sys, 'frozen', frozen, raising=False)
    monkeypatch.setattr(sys, 'executable', r'C:\Program Files\Unshrimp\unshrimp.exe' if frozen else r'C:\Python\python.exe')
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
