import sys, copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0, str(Path.cwd()))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette, QIcon
import config
from unshrimp.core.states import State
from unshrimp.core.breaks import BreakReminder
from unshrimp.ui.main_window import MainWindow
from unshrimp.ui.settings import SettingsDialog
from unshrimp.ui import theme
app = QApplication([])
controller = Mock()
controller.cfg = copy.deepcopy(config.DEFAULTS)
controller.machine = SimpleNamespace(state=State.GOOD)
controller.log.day_summaries.return_value = []
controller.worker.isRunning.return_value = True
controller.baseline = SimpleNamespace(created_at=None)
controller._suspended = controller._idle_stopped = False
controller._cal = None
controller._display_deviation = .2
controller.breaks = BreakReminder(True,2400)
main = MainWindow(controller)
settings = SettingsDialog(controller.cfg, controller)
out = Path('docs/audits/header-review-2026-10-17')
def capture():
    main.grab().save(str(out/'01-main.png'))
    settings.grab().save(str(out/'02-settings.png'))
    print('titles', main.windowTitle(), settings.windowTitle(), 'icon', theme.app_icon().isNull(), 'palette', {r:main.palette().color(getattr(QPalette,r)).name() for r in ['Window','Highlight']}, flush=True)
    settings.close(); app.quit()
main.show()
settings.show()
QTimer.singleShot(500,capture)
app.exec()
