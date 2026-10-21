"""Saved settings may be hand-edited or left in an older shape."""
import json

import config
import pytest


def test_loaded_defaults_are_independent_nested_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "missing.json")
    first, second = config.load(), config.load()
    original_name = config.DEFAULTS["exercises"][0]["name"]
    first["exercises"][0]["name"] = "Custom suggestion"
    first["hud"]["size"] = "l"
    assert second["exercises"][0]["name"] == original_name
    assert config.DEFAULTS["exercises"][0]["name"] == original_name
    assert second["hud"]["size"] == config.DEFAULTS["hud"]["size"]


@pytest.mark.parametrize("has_current_history", [False, True])
def test_legacy_migration_never_overwrites_current_history(tmp_path, monkeypatch, has_current_history):
    legacy, current = tmp_path / "OSA", tmp_path / "Shrimply"
    legacy.mkdir()
    current.mkdir()
    (legacy / "config.json").write_text('{"fps": 4}', encoding="utf-8")
    (legacy / "log.db").write_bytes(b"old history")
    if has_current_history:
        (current / "log.db").write_bytes(b"newer history")
    monkeypatch.setattr(config, "APP_DIR", current)
    monkeypatch.setattr(config, "LEGACY_APP_DIR", tmp_path / "Unshrimp")
    monkeypatch.setattr(config, "CONFIG_PATH", current / "config.json")
    monkeypatch.setattr(config, "_data_dir", lambda _: legacy)

    config.migrate_legacy()

    assert config.load()["fps"] == 4
    assert (current / "log.db").read_bytes() == (b"newer history" if has_current_history else b"old history")
    assert (legacy / "log.db").read_bytes() == b"old history"


def test_rename_keeps_existing_settings_and_history(tmp_path, monkeypatch):
    old = tmp_path / "Unshrimp"
    older = tmp_path / "OSA"
    new = tmp_path / "Shrimply"
    old.mkdir()
    older.mkdir()
    new.mkdir()
    (old / "config.json").write_text('{"welcome_seen": true}', encoding="utf-8")
    (old / "log.db").write_bytes(b"history")
    (older / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(config, "APP_DIR", new)
    monkeypatch.setattr(config, "LEGACY_APP_DIR", old)
    monkeypatch.setattr(config, "_data_dir", lambda name: tmp_path / name)

    config.migrate_legacy()
    assert (new / "config.json").read_bytes() == (old / "config.json").read_bytes()
    assert (new / "log.db").read_bytes() == b"history"
    (new / "config.json").write_text("saved later", encoding="utf-8")
    config.migrate_legacy()
    assert (new / "config.json").read_text(encoding="utf-8") == "saved later"


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


def test_oversized_json_numbers_fall_back_without_crashing(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"fps": 10**400, "sensitivity": -(10**400)}))
    monkeypatch.setattr(config, "CONFIG_PATH", path)
    loaded = config.load()
    assert loaded["fps"] == config.DEFAULTS["fps"]
    assert loaded["sensitivity"] == config.DEFAULTS["sensitivity"]
