"""Isolate native camera startup stages; record metadata, never images."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import cv2
from PySide6.QtCore import QLockFile, QThread, QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=int, default=12)
    parser.add_argument('--gap', type=float, default=0.)
    parser.add_argument('--no-size', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin' or args.cycles < 1 or args.gap < 0 or args.output.exists():
        parser.error('Requires macOS, positive cycles, nonnegative gap, and a fresh output')
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(str(config.APP_DIR / 'instance.lock'))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        parser.error('Quit Shrimply before probing capture')
    rows = []

    class Probe(QThread):
        def run(self):
            row = {'cycle': len(rows) + 1, 'reads': []}
            start = time.monotonic()
            cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
            try:
                row['open_ms'] = round(1000 * (time.monotonic() - start), 1)
                row['opened'] = cap.isOpened()
                row['size'] = [cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)]
                def read(stage):
                    before = time.monotonic()
                    ok, frame = cap.read()
                    row['reads'].append({'stage': stage, 'ok': bool(ok and frame is not None),
                                         'ms': round(1000 * (time.monotonic() - before), 1),
                                         'shape': list(frame.shape) if ok and frame is not None else None})
                read('before_size')
                if not args.no_size:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                for _ in range(3):
                    read('after_size' if not args.no_size else 'unchanged')
            finally:
                cap.release()
                rows.append(row)
                print(json.dumps(row), flush=True)

    workers = []
    def next_cycle():
        if workers and not workers[-1].wait(0):
            QTimer.singleShot(10, next_cycle)
        elif len(rows) >= args.cycles:
            app.quit()
        else:
            worker = Probe()
            workers.append(worker)
            worker.finished.connect(lambda: QTimer.singleShot(round(args.gap * 1000), next_cycle))
            worker.start()
    QTimer.singleShot(0, next_cycle)
    app.exec()
    for worker in workers:
        worker.wait()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'opencv': cv2.__version__, 'gap': args.gap,
                                      'configure_size': not args.no_size, 'cycles': rows}, indent=2))
    lock.unlock()


if __name__ == '__main__':
    main()
