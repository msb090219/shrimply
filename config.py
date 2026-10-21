"""Config persistence — one small JSON file, in the platform's proper place.

Windows: %APPDATA%\\Shrimply · macOS: ~/Library/Application Support/Shrimply ·
elsewhere: ~/.config/Shrimply. Posture baselines and settings live here,
outside the repo, and never leave the machine.

Shrimply carries settings and history forward from Unshrimp (and older OSA)
without removing the old folders.
"""
from __future__ import annotations

import json
import copy
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

APP_NAME = "Shrimply"


def _data_dir(app_name: str) -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / app_name


APP_DIR = _data_dir(APP_NAME)
LEGACY_APP_DIR = _data_dir("Unshrimp")
CONFIG_PATH = APP_DIR / "config.json"


def migrate_legacy() -> None:
    """Copy missing settings/history from the newest previous app folder."""
    for name in ("config.json", "log.db"):
        dst = APP_DIR / name
        if dst.exists():
            continue
        for legacy in (LEGACY_APP_DIR, _data_dir("OSA")):
            src = legacy / name
            if src.is_file():
                try:
                    APP_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                except OSError:
                    pass
                break

DEFAULTS: dict = {
    "camera_index": 0,
    "tracking_paused": False,
    "welcome_seen": False,
    "fps": 2.0,
    "sensitivity": 1.0,
    # mirrors core.Thresholds; kept flat for a human-editable file
    "drift": 1.0,
    "bad": 1.5,
    "grace_s": 45.0,
    "renag_s": 120.0,
    "away_s": 15.0,
    "recovery_s": 10.0,
    "sound_on": False,
    "toasts_enabled": True,
    "mascot_enabled": True,
    "mascot_style": "shrimp",  # shrimp | text
    "mascot_size": "m",  # s | m | l
    "mascot_opacity": 0.87,
    "mascot_bob": True,
    "mascot_entrance": "rise",  # rise | fade | instant
    "mascot_bad_hold_s": 2,
    "mascot_recovery_hold_s": 3,
    "mascot_position": "center",
    "mascot_screen": "",
    "reduce_motion": False,
    "theme_mode": "dark",
    "reminder_enabled": True,
    "reminder_interval_min": 40,
    "reminder_break_min": 2,
    "exercises": [
        {
            "name": "Chin tucks",
            "how": "Glide your head straight back (keep looking ahead). 10 slow reps.",
        },
        {
            "name": "Thoracic extension",
            "how": "Hands behind head, arch gently over the backrest. Breathe.",
        },
        {
            "name": "Wall angels",
            "how": "Back flat on a wall, slide arms up and down, keeping contact.",
        },
        {
            "name": "Doorway pec stretch",
            "how": "Forearm on the doorframe, gentle stretch, turn slightly away.",
        },
        {
            "name": "Scapular squeezes",
            "how": "Draw shoulder blades down and together. Hold 5s × 10.",
        },
    ],
    "hud": {"x": None, "y": None, "visible": True, "compact": False, "size": "m", "orientation": "horizontal", "opacity": 1.0},
    "baseline": None,  # Baseline.to_dict() once calibrated
}


def _valid(key: str, value) -> bool:
    choices = {
        "theme_mode": ("dark", "light", "system"),
        "mascot_style": ("shrimp", "text"),
        "mascot_size": ("s", "m", "l"),
        "mascot_entrance": ("rise", "fade", "instant"),
        "mascot_position": ("left", "center", "right", "top_left", "top_center", "top_right", "middle"),
        "size": ("s", "m", "l"),
        "orientation": ("horizontal", "vertical"),
    }
    if key in choices:
        return value in choices[key]
    if key in ("fps", "sensitivity", "drift", "bad", "grace_s", "renag_s",
               "away_s", "recovery_s", "mascot_opacity", "opacity"):
        limit = (30 if key == "fps" else 1 if key in ("mascot_opacity", "opacity")
                 else 10 if key in ("sensitivity", "drift", "bad") else 86400)
        return (type(value) in (int, float)
                and (value > 0 if key in ("fps", "sensitivity", "drift", "bad") else value >= 0)
                and value <= limit and math.isfinite(value))
    if key in ("camera_index", "reminder_interval_min", "reminder_break_min",
               "mascot_bad_hold_s", "mascot_recovery_hold_s"):
        limit = (99 if key == "camera_index" else 15 if key.startswith("mascot_")
                 else 180 if key == "reminder_interval_min" else 30)
        minimum = 0 if key == "camera_index" or key.startswith("mascot_") else 1
        return type(value) is int and minimum <= value <= limit
    if key in ("x", "y"):
        return value is None or (type(value) is int and abs(value) <= 1000000)
    if key == "baseline":
        return value is None or isinstance(value, dict)
    if key == "exercises":
        return (isinstance(value, list) and all(isinstance(item, dict)
                and isinstance(item.get("name"), str) and isinstance(item.get("how"), str)
                for item in value))
    if key in ("mascot_screen",):
        return isinstance(value, str)
    default = DEFAULTS.get(key, DEFAULTS["hud"].get(key))
    return type(value) is type(default)


def load() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, v in data.items():
                if k == "hud" and isinstance(v, dict):
                    for name, item in v.items():
                        if name in cfg["hud"] and _valid(name, item):
                            cfg["hud"][name] = item
                elif k in cfg and k != "hud" and _valid(k, v):
                    cfg[k] = v
        if cfg["bad"] <= cfg["drift"]:
            cfg["drift"] = DEFAULTS["drift"]
            cfg["bad"] = DEFAULTS["bad"]
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass  # first run or corrupt file — defaults are fine
    return cfg


def save(cfg: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    # atomic write so a crash mid-save can't corrupt the file
    fd, tmp = tempfile.mkstemp(dir=APP_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
