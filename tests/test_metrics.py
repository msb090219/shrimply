"""Unit tests for unshrimp.vision.metrics — synthetic poses, no camera needed."""
from __future__ import annotations

from dataclasses import dataclass, field
import math

import pytest


@dataclass
class P:  # a normalized landmark
    x: float
    y: float
    z: float = 0.0
    visibility: float | None = 1.0
    presence: float | None = 1.0


def pose(ear_y: float, sh_y: float, sh_halfw: float = 0.18):
    """Build the 4 landmarks metrics cares about (rest are dummy)."""
    lms = [P(0.5, 0.5) for _ in range(33)]
    lms[11] = P(0.5 - sh_halfw, sh_y)
    lms[12] = P(0.5 + sh_halfw, sh_y)
    lms[7] = P(0.45, ear_y)
    lms[8] = P(0.55, ear_y)
    return lms


def face(face_halfw: float):
    """Face landmarks: cheeks set face width; rest dummy. 478 points."""
    lms = [P(0.5, 0.4) for _ in range(478)]
    lms[234] = P(0.5 - face_halfw, 0.4)
    lms[454] = P(0.5 + face_halfw, 0.4)
    return lms


IDENTITY_MATRIX = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def signals(ear_y, sh_y, face_halfw, matrix=IDENTITY_MATRIX, sh_halfw=0.18):
    from unshrimp.vision.metrics import compute_signals

    return compute_signals(pose(ear_y, sh_y, sh_halfw), face(face_halfw), matrix)


def test_good_pose_scores():
    s = signals(ear_y=0.30, sh_y=0.60, face_halfw=0.07)
    assert s.ok
    assert s.rejection_reason is None
    assert s.head_pitch == 0.0 and s.head_yaw == 0.0 and s.head_roll == 0.0
    # ears well above shoulders: sink = (0.60-0.30)/0.36 ≈ 0.833
    assert abs(s.head_sink - 0.8333) < 0.001
    # face/shoulder ratio = 0.14/0.36 ≈ 0.389
    assert abs(s.lean_in - 0.3889) < 0.001


def test_hunching_decreases_sink_and_increases_lean():
    """The core medical claim of the app, as geometry."""
    tall = signals(ear_y=0.30, sh_y=0.60, face_halfw=0.07)
    hunched = signals(ear_y=0.42, sh_y=0.55, face_halfw=0.10)  # ears drop, face closer/bigger
    assert hunched.head_sink < tall.head_sink
    assert hunched.lean_in > tall.lean_in


def test_missing_any_model_yields_not_ok():
    from unshrimp.vision.metrics import compute_signals

    assert compute_signals(None, face(0.07), IDENTITY_MATRIX).rejection_reason == "missing_detection"
    assert not compute_signals(pose(0.3, 0.6), None, IDENTITY_MATRIX).ok
    assert not compute_signals(pose(0.3, 0.6), face(0.07), None).ok


def test_too_far_away_not_ok():
    # shoulder width below the noise floor (person too far / turned away)
    result = signals(ear_y=0.3, sh_y=0.6, face_halfw=0.07, sh_halfw=0.01)
    assert not result.ok
    assert result.rejection_reason == "shoulder_span"


def test_euler_identity_and_simple_rotations():
    import math

    from unshrimp.vision.metrics import euler_from_matrix

    assert all(abs(a) < 1e-9 for a in euler_from_matrix(IDENTITY_MATRIX))

    def rot_x(deg):
        r = math.radians(deg)
        c, s = math.cos(r), math.sin(r)
        return [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, c, -s, 0.0],
            [0.0, s, c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]

    pitch, _, _ = euler_from_matrix(rot_x(10))
    assert abs(pitch - 10.0) < 1e-6


@pytest.mark.parametrize("index", [7, 8, 11, 12])
@pytest.mark.parametrize("field_name", ["visibility", "presence"])
@pytest.mark.parametrize("value", [0.49, None, float("nan"), float("inf"), -1., 1.1])
def test_each_required_pose_point_must_have_reliable_confidence(index, field_name, value):
    from unshrimp.vision.metrics import compute_signals

    points = pose(.3, .6)
    setattr(points[index], field_name, value)
    result = compute_signals(points, face(.07), IDENTITY_MATRIX)
    assert not result.ok
    assert result.rejection_reason == "pose_confidence"
    assert result.face_found and result.pose_found
    assert result.head_pitch is None
    assert result.head_sink is None
    assert result.lean_in is None


def test_confidence_boundary_and_unneeded_points():
    from unshrimp.vision.metrics import compute_signals

    points = pose(.3, .6)
    points[7].visibility = .5
    points[12].presence = .6
    points[25].visibility = 0.  # hidden knees are irrelevant to the posture signals
    result = compute_signals(points, face(.07), IDENTITY_MATRIX)
    assert result.ok
    assert result.pose_visibility == .5
    assert result.pose_presence == .6


@pytest.mark.parametrize("index,is_face", [(7, False), (8, False), (11, False), (12, False), (234, True), (454, True)])
@pytest.mark.parametrize("coordinate", ["x", "y"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), None, -.1, 1.1])
def test_required_points_must_be_finite_and_in_frame(index, is_face, coordinate, value):
    from unshrimp.vision.metrics import compute_signals

    pose_points, face_points = pose(.3, .6), face(.07)
    setattr((face_points if is_face else pose_points)[index], coordinate, value)
    result = compute_signals(pose_points, face_points, IDENTITY_MATRIX)
    assert not result.ok
    name = {7: "left_ear", 8: "right_ear", 11: "left_shoulder", 12: "right_shoulder",
            234: "left_cheek", 454: "right_cheek"}[index]
    category = "out_of_frame" if value in (-.1, 1.1) else "invalid_coordinate"
    assert result.rejection_reason == f"{category}:{name}"


def test_nonfinite_orientation_and_collapsed_face_are_unscorable():
    from unshrimp.vision.metrics import compute_signals

    matrix = [row[:] for row in IDENTITY_MATRIX]
    matrix[0][0] = math.nan
    assert compute_signals(pose(.3, .6), face(.07), matrix).rejection_reason == "invalid_orientation"
    assert compute_signals(pose(.3, .6), face(0.), IDENTITY_MATRIX).rejection_reason == "face_span"


def test_missing_required_landmark_arrays_are_unscorable():
    from unshrimp.vision.metrics import compute_signals

    assert compute_signals([], face(.07), IDENTITY_MATRIX).rejection_reason == "incomplete_landmarks"
    assert not compute_signals(pose(.3, .6), [], IDENTITY_MATRIX).ok
    assert not compute_signals(pose(.3, .6), face(.07), []).ok


def test_face_confidence_is_optional_but_pose_confidence_is_required():
    from unshrimp.vision.metrics import compute_signals

    points = face(.07)
    for index in (234, 454):
        points[index].visibility = points[index].presence = None
    assert compute_signals(pose(.3, .6), points, IDENTITY_MATRIX).ok


def test_rejected_pose_never_enters_scoring_or_calibration():
    from unshrimp.core.baseline import Baseline
    from unshrimp.core.calibration import CalibrationSession
    from unshrimp.vision.metrics import compute_signals

    points = pose(.3, .6)
    points[11].visibility = .1
    rejected = compute_signals(points, face(.07), IDENTITY_MATRIX)
    assert Baseline().deviation(rejected) is None
    calibration = CalibrationSession()
    calibration.force_continue(0.)
    events = []
    for second in range(12):
        result = calibration.feed(rejected, float(second))
        events.extend(result.events)
    assert result.phase == "tall"
    assert result.progress == "Collection paused"
    assert "failed:too_few" not in events
    assert calibration._tall_total == 0
