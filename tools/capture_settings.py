"""Capture the real settings widgets with isolated data and no camera capture."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QPushButton
import config
from shrimply.ui.app import ShrimplyApp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    report = []
    with tempfile.TemporaryDirectory(prefix='shrimply-settings-') as folder:
        data = Path(folder)
        with (patch.object(config, 'APP_DIR', data),
              patch.object(config, 'CONFIG_PATH', data / 'config.json')):
            cfg = copy.deepcopy(config.DEFAULTS)
            cfg.update(tracking_paused=True, welcome_seen=True, mascot_enabled=False)
            cfg['hud']['visible'] = False
            config.save(cfg)
            controller = ShrimplyApp(ROOT / 'models')
            try:
                controller._open_settings()
                window, dialog = controller.main_window, controller._settings_dlg
                def capture(name):
                    app.processEvents()
                    assert window.grab().save(str(args.output / f'{name}.png'))
                for mode in ('light', 'dark'):
                    dialog.theme_mode.setCurrentIndex(dialog.theme_mode.findData(mode))
                    for width in (620, 960):
                        window.resize(width, 680)
                        for page in ('Tracking', 'Alerts and breaks', 'Appearance', 'General'):
                            dialog.select_page(page)
                            app.processEvents()
                            scroll = dialog.tabs.currentWidget()
                            tag = f'{mode}-{width}-{page.split()[0].lower()}'
                            scroll.verticalScrollBar().setValue(0)
                            capture(tag + '-top')
                            if page == 'Alerts and breaks':
                                scroll.ensureWidgetVisible(dialog.ex_remove, 0, 25)
                                capture(tag + '-editor')
                                assert dialog.ex_editor.grab().save(str(args.output / f'{tag}-editor-detail.png'))
                                buttons = [b for b in dialog.ex_name.parentWidget().findChildren(QPushButton)
                                           if b.text() in ('Add', 'Update', 'Remove')]
                                report.append({'theme': mode, 'width': width,
                                               'tab_bar_x': dialog.tabs.tabBar().x(),
                                               'list_height': dialog.ex_list.height(),
                                               'list_parent_height': dialog.ex_list.parentWidget().height(),
                                               'list_minimum': dialog.ex_list.parentWidget().minimumSizeHint().height(),
                                               'buttons': {b.text(): [b.x(), b.y(), b.width(), b.height()]
                                                           for b in buttons}})
                            scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                            capture(tag + '-bottom')
                window.dashboard_button.click()
                for width in (620, 960):
                    window.resize(width, 680)
                    capture(f'dashboard-{width}')
                from shrimply.ui import theme
                from shrimply.ui.welcome import WelcomeDialog
                from shrimply.ui.preview import PreviewWindow
                from shrimply.ui.break_prompt import BreakPrompt
                for mode in ('light', 'dark'):
                    theme.set_mode(mode)
                    for widget, name in ((WelcomeDialog(about_mode=True), 'about'),
                                         (PreviewWindow(), 'calibration'),
                                         (BreakPrompt(example=True), 'break-reminder')):
                        if name == 'calibration':
                            from shrimply.ui.app import _CAL_INSTRUCTIONS
                            widget.set_instruction(*_CAL_INSTRUCTIONS['enter_tall'])
                            widget.set_phase('tall')
                        widget.show()
                        app.processEvents()
                        assert widget.grab().save(str(args.output / f'{mode}-{name}.png'))
                        widget.hide()
                        widget.deleteLater()
            finally:
                controller.shutdown()
                if controller._settings_dlg is not None:
                    controller._settings_dlg.close()
                for widget in app.topLevelWidgets():
                    widget.hide()
                controller.tray.icon.hide()
    (args.output / 'geometry.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
