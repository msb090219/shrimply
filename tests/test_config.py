"""Saved settings may be hand-edited or left in an older shape."""
import json

import config


def test_invalid_startup_settings_fall_back_without_rewriting_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    saved = {"fps": 0, "hud": None, "camera_index": "zero",
             "sensitivity": "high", "theme_mode": [], "reminder_interval_min": -1,
             "mascot_opacity": float("inf"), "tracking_paused": "false"}
    path.write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", path)

    loaded = config.load()

    for key in saved:
        assert loaded[key] == config.DEFAULTS[key]
    assert json.loads(path.read_text(encoding="utf-8")) == saved


def test_valid_settings_and_hud_fields_survive_invalid_neighbors(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"fps": 4, "hud": {"size": "l", "visible": False,
                                                      "opacity": "opaque", "x": "left"},
                                "mascot_style": "text", "bad": 1.8}), encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", path)

    loaded = config.load()

    assert loaded["fps"] == 4
    assert loaded["mascot_style"] == "text"
    assert loaded["bad"] == 1.8
    assert loaded["hud"]["size"] == "l"
    assert loaded["hud"]["visible"] is False
    assert loaded["hud"]["opacity"] == config.DEFAULTS["hud"]["opacity"]
    assert loaded["hud"]["x"] is None


def test_non_object_json_uses_defaults(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("null", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    assert config.load()["fps"] == config.DEFAULTS["fps"]


def test_non_utf8_config_uses_defaults_without_rewriting_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_bytes(b"\xff")
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    assert config.load()["fps"] == config.DEFAULTS["fps"]
    assert path.read_bytes() == b"\xff"
