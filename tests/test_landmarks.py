from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from unshrimp.vision.landmarks import Landmarkers


def landmarker():
    points = [SimpleNamespace(x=.5, y=.3, visibility=1., presence=1.) for _ in range(33)]
    points[11].x, points[11].y = .3, .6
    points[12].x, points[12].y = .7, .6
    face = [SimpleNamespace(x=.5, y=.3) for _ in range(478)]
    face[234].x, face[454].x = .4, .6
    model = object.__new__(Landmarkers)
    model._pose = Mock()
    model._face = Mock()
    model._pose.detect_for_video.return_value = SimpleNamespace(pose_landmarks=[points])
    model._face.detect_for_video.return_value = SimpleNamespace(
        face_landmarks=[face], facial_transformation_matrixes=[np.eye(4)])
    return model, points


def test_valid_landmarks_keep_the_preview_overlay():
    model, _ = landmarker()
    signals, overlay = model.signals_with_overlay(np.zeros((48, 64, 3), dtype=np.uint8), 1)
    assert signals.ok
    assert len(overlay) == 4


@pytest.mark.parametrize("field,value", [("visibility", .1), ("x", float("nan")), ("y", 1.1)])
def test_rejected_points_do_not_reach_preview_integer_conversion(field, value):
    model, points = landmarker()
    setattr(points[7], field, value)
    signals, overlay = model.signals_with_overlay(np.zeros((48, 64, 3), dtype=np.uint8), 1)
    assert not signals.ok
    assert overlay is None
