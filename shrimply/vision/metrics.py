"""Pure posture-signal math.

No MediaPipe imports here — functions take plain landmark coordinates so the
geometry is unit-testable with synthetic poses (see tests/test_metrics.py).

All ratios are normalized by the inter-shoulder distance, making them
invariant to camera distance and framing zoom. Coordinates follow MediaPipe's
normalized image space: x in [0,1] left→right, y in [0,1] top→bottom
(so a *larger* y is *lower* on screen).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

# MediaPipe Pose landmark indices (33-point model)
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_EAR = 7
RIGHT_EAR = 8

# FaceLandmarker indices (478-point model) — outer cheek points, roughly
# in front of each ear; their horizontal span is a good face-width proxy.
LEFT_CHEEK = 234
RIGHT_CHEEK = 454

# Below this normalized shoulder width the person is too far away / too
# turned for the ratios to mean anything.
_MIN_SHOULDER_W = 0.04
# shortcut: model confidence can miss physical occlusion; validate more camera conditions before release.
_MIN_POSE_CONFIDENCE = 0.5
_REQUIRED_POSE = (LEFT_EAR, RIGHT_EAR, LEFT_SHOULDER, RIGHT_SHOULDER)


@dataclass(frozen=True)
class FrameSignals:
    """Posture signals for one frame. `ok` False means "don't score this frame".

    face_found / pose_found stay informative even when ok is False, so callers
    can tell "nobody's at the desk" from "present but unreadable".
    """

    ok: bool
    face_found: bool = False
    pose_found: bool = False
    head_pitch: float | None = None  # degrees, head rotation about x-axis
    head_yaw: float | None = None
    head_roll: float | None = None
    head_sink: float | None = None  # (shoulder_y - ear_y)/shoulder_w; larger = sitting taller
    lean_in: float | None = None  # face_w/shoulder_w; larger = poking toward the screen
    shoulder_w: float | None = None  # normalized inter-shoulder distance (framing check)
    luminance: float | None = None  # mean frame brightness 0-255 (lighting check)
    pose_visibility: float | None = None  # minimum confidence over required pose points
    pose_presence: float | None = None
    rejection_reason: str | None = None  # diagnostics only; ok remains the scoring gate


def euler_from_matrix(m) -> tuple[float, float, float]:
    """Head orientation (pitch, yaw, roll in degrees) from the FaceLandmarker
    4x4 facial transformation matrix (nested lists).

    Uses the standard Rz·Ry·Rx decomposition; the absolute sign convention is
    pinned empirically during calibration (baseline.bad_dirs), so any global
    flip cancels out in deviation scoring.
    """
    r00, r01, r02 = m[0][0], m[0][1], m[0][2]
    r10, r11, _ = m[1][0], m[1][1], m[1][2]
    r20, r21, r22 = m[2][0], m[2][1], m[2][2]

    sy = math.sqrt(r00 * r00 + r10 * r10)
    singular = sy < 1e-6
    if not singular:
        pitch = math.atan2(r21, r22)
        yaw = math.atan2(-r20, sy)
        roll = math.atan2(r10, r00)
    else:  # pitch ≈ ±90°, gimbal lock — roll degenerates
        pitch = math.atan2(-m[1][2], r11)
        yaw = math.atan2(-r20, sy)
        roll = 0.0
    return tuple(math.degrees(a) for a in (pitch, yaw, roll))


def compute_signals(pose_lms, face_lms, face_matrix) -> FrameSignals:
    """Combine one frame of landmarks into the posture signals.

    Args may be None (model didn't detect); any None → ok=False, no scoring.
    """
    face_found = face_lms is not None and face_matrix is not None
    pose_found = pose_lms is not None
    if not (face_found and pose_found):
        return FrameSignals(ok=False, face_found=face_found, pose_found=pose_found,
                            rejection_reason="missing_detection")

    rejected = FrameSignals(ok=False, face_found=True, pose_found=True)
    if (len(pose_lms) <= max(_REQUIRED_POSE) or len(face_lms) <= max(LEFT_CHEEK, RIGHT_CHEEK)
            or len(face_matrix) < 3 or any(len(row) < 3 for row in face_matrix[:3])):
        return replace(rejected, rejection_reason="incomplete_landmarks")
    points = [pose_lms[index] for index in _REQUIRED_POSE]
    confidence = {}
    for name in ("visibility", "presence"):
        values = [getattr(point, name, None) for point in points]
        confidence[name] = (min(values) if all(
            value is not None and math.isfinite(value) and 0 <= value <= 1
            for value in values) else None)
    rejected = replace(rejected, pose_visibility=confidence["visibility"],
                       pose_presence=confidence["presence"])
    if any(value is None or value < _MIN_POSE_CONFIDENCE for value in confidence.values()):
        return replace(rejected, rejection_reason="pose_confidence")
    required = [("left_ear", pose_lms[LEFT_EAR]), ("right_ear", pose_lms[RIGHT_EAR]),
                ("left_shoulder", pose_lms[LEFT_SHOULDER]), ("right_shoulder", pose_lms[RIGHT_SHOULDER]),
                ("left_cheek", face_lms[LEFT_CHEEK]), ("right_cheek", face_lms[RIGHT_CHEEK])]
    for name, point in required:
        if any(value is None or not math.isfinite(value) for value in (point.x, point.y)):
            return replace(rejected, rejection_reason=f"invalid_coordinate:{name}")
        if any(not 0 <= value <= 1 for value in (point.x, point.y)):
            return replace(rejected, rejection_reason=f"out_of_frame:{name}")
    if any(value is None or not math.isfinite(value) for row in face_matrix[:3] for value in row[:3]):
        return replace(rejected, rejection_reason="invalid_orientation")

    ls, rs = pose_lms[LEFT_SHOULDER], pose_lms[RIGHT_SHOULDER]
    shoulder_w = math.hypot(rs.x - ls.x, rs.y - ls.y)
    if shoulder_w < _MIN_SHOULDER_W:
        return replace(rejected, rejection_reason="shoulder_span")

    shoulder_y = (ls.y + rs.y) / 2
    ear_y = (pose_lms[LEFT_EAR].y + pose_lms[RIGHT_EAR].y) / 2
    head_sink = (shoulder_y - ear_y) / shoulder_w

    lc, rc = face_lms[LEFT_CHEEK], face_lms[RIGHT_CHEEK]
    face_w = abs(rc.x - lc.x)
    if face_w == 0:
        return replace(rejected, rejection_reason="face_span")
    lean_in = face_w / shoulder_w

    pitch, yaw, roll = euler_from_matrix(face_matrix)

    return replace(
        rejected,
        ok=True,
        head_pitch=pitch,
        head_yaw=yaw,
        head_roll=roll,
        head_sink=head_sink,
        lean_in=lean_in,
        shoulder_w=shoulder_w,
    )
