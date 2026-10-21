import json
from unittest.mock import Mock

from shrimply import diag


def test_numeric_diagnostics_are_opt_in(monkeypatch):
    output = Mock()
    monkeypatch.setattr(diag, "log", output)
    monkeypatch.setattr(diag, "_detailed", False)
    diag.sample("posture", deviation=.2)
    output.assert_not_called()
    monkeypatch.setattr(diag, "_detailed", True)
    diag.sample("posture", deviation=.2)
    record = json.loads(output.call_args.args[0])
    assert record["kind"] == "posture"
    assert record["deviation"] == .2
    assert record["monotonic"] > 0
