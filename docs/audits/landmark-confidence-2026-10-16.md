# Required-landmark confidence check

16 October 2026, Windows, local camera 0, source diagnostic tool. Unshrimp was
manually paused before testing. No camera images or video were saved.

Required ears and shoulders now need both visibility and presence >= 0.5.
Missing/nonfinite confidence, invalid orientation, out-of-frame required x/y,
collapsed face width, and insufficient shoulder span make the frame unscorable.
Face confidence is optional in MediaPipe's face output, so it is not required.
Rejected points do not enter scoring/calibration or draw preview markers.
Worker diagnostics include the minimum required pose visibility/presence.

Each run used `tools/vision_demo.py --seconds 8 --camera 0 --report PATH` at
2 fps. Reports contain only numeric measurements and detection flags.

| Condition | Report | Accepted | Observation |
|---|---|---|---|
| Normal sitting | `diagnostics/landmark-normal.json` | 16/16 | Visibility approximately 0.999–1.000, presence 0.995–0.999. |
| One ear covered by palm, user confirmed | `diagnostics/landmark-ear-covered.json` | 16/16 | Visibility approximately 0.999, presence 0.996–0.999. Physical occlusion was not rejected. |
| Shoulder out of view, preview-assisted, user confirmed completion | `diagnostics/landmark-shoulder-preview.json` | 10/16 | Six frames rejected as unreliable/framing; visibility approximately 0.999 and presence 0.992–0.999 throughout. No read failures or lost model detections. |
| Normal baseline with rejection diagnostics | `diagnostics/landmark-normal-reasons.json` | 16/16 | No rejections or read failures; visibility approximately 0.999, presence 0.988–0.997. |
| Shoulder check with rejection diagnostics | `diagnostics/landmark-shoulder-reasons.json` | 15/16 | One rejection at approximately 1.001 s: `out_of_frame:left_shoulder`. Visibility approximately 0.997–0.998, presence 0.980–0.995. |
| Return to normal with rejection diagnostics | `diagnostics/landmark-recovery-reasons.json` | 16/16 | No rejections or read failures; visibility approximately 0.999, presence 0.992–0.997. |

The shoulder run used `--preview`: the user could inspect framing and press Space
to begin the eight-second measurement. The preview closed and camera released
at completion. No frames were retained to independently verify how long the
anatomical shoulder landmark was outside the image (the shoulder's outer edge
and the model's shoulder joint are different). The report does not identify the
specific geometry guard responsible for rejection. It establishes intermittent
geometry rejection, not reliable rejection of the entire obstructed interval.

The normal test supports retaining clean frames at the provisional 0.5 threshold.
It does not establish that threshold's rejection accuracy. The confidence ranges
overlap: increasing the threshold to reject the covered-ear run is unsupported.
Model confidence is not ground truth for whether a landmark is visible.
T08 remains open until occlusion handling has suitable evidence; do not claim
that hidden required points are reliably rejected by the current implementation.

Automated verification: 223 tests pass, including preview start/cancel cleanup and each required pose point's
visibility/presence, threshold boundaries, malformed geometry, optional face
confidence, scoring/calibration exclusion, preview safety, and numeric report
cleanup. Synthetic confidence tests establish the gate's behavior, not the
model's accuracy. This source change is not yet in the packaged executable.

## Follow-up investigation

The app passes RGB pixels to MediaPipe and reads each required landmark's
visibility/presence without transforming those values. The installed Python
wrapper copies the native fields directly. The local pose task SHA-256 is
`59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a`, matching
`fetch_models.py`. No confidence-field mix-up or incorrect model file was found.

Google's [model card](https://developers.google.com/ml-kit/images/vision/pose-detection/pose_model_card.pdf)
distinguishes presence (in-frame probability) from visibility (in-frame and
unobstructed probability). A covered ear can remain present. High visibility in
that case is an incorrect confidence estimate relative to the user's reported
obstruction, not evidence that the ear was visible.

The upstream [pose graph](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/pose_landmarker/pose_landmarks_detector_graph.cc)
applies sigmoid activation to pose confidence outputs and, when smoothing is
enabled, filters visibility with alpha 0.1. Tracking/smoothing could affect
transitions, but the earlier reports cannot isolate it from model overconfidence
or uncertainty about anatomical landmark framing. Upstream main source is
context, not proof of the exact native graph shipped in the installed wheel.
Pose-wide detection/presence/tracking thresholds are not per-landmark obstruction
detectors. Do not change them or raise the landmark threshold without evidence.

The old report discarded the reason a frame failed. New source diagnostics and
JSON reports retain `rejection_reason`: missing detection, incomplete landmarks,
pose confidence, invalid coordinate (named point), out-of-frame (named point),
invalid orientation, shoulder span, or face span. Accepted frames have no reason.
This makes a repeat shoulder run informative without saving camera images.
It cannot retrospectively identify the cause of the six earlier rejections.

The preview-assisted normal / shoulder-out-of-view / normal sequence is now
complete (the three `*-reasons.json` reports above). Each condition used a fresh
process/model instance. Normal acceptance after repositioning is confirmed; this
does not test recovery within the same tracking instance. All three released
the camera and exited zero; that exit code only means some frames were accepted.
The shoulder run proves that the coordinate guard rejects a predicted joint
outside the image even when confidence is high. Its 15 accepted frames do not
establish that the physical joint was visible: model predictions and exact human
framing cannot be independently checked from these numeric reports. Consistent
obstruction rejection has not passed. Further identical short holds would not
isolate the cause.

## Same-frame IMAGE versus VIDEO comparison

Completed with `tools/compare_pose_modes.py --camera 0 --seconds 8 --report
diagnostics/pose-mode-comparison.json`. The user confirmed completion. Exit 0;
all three stages completed, with 51 paired frames (17 per stage). Both models
used the same RGB pixels and stayed alive across the full sequence, including
preparation. Camera/models/window were released at the end. No images saved.

| Stage | Mode | Pose found | All required x/y in frame | All required confidence >= 0.5 |
|---|---|---|---|---|
| Normal | VIDEO | 17/17 | 17/17 | 17/17 |
| Normal | IMAGE | 17/17 | 17/17 | 17/17 |
| Shoulder out | VIDEO | 17/17 | 6/17 | 17/17 |
| Shoulder out | IMAGE | 17/17 | 9/17 | 17/17 |
| Normal return | VIDEO | 17/17 | 17/17 | 17/17 |
| Normal return | IMAGE | 17/17 | 17/17 | 17/17 |

Every out-of-frame prediction named the left shoulder. During shoulder-out,
VIDEO minimum required visibility ranged 0.991–0.992 and IMAGE 0.994–0.998;
minimum presence across that stage was 0.948 and 0.972 respectively. Thus even
independent detection can produce high confidence for a predicted joint outside
the image. Temporal tracking is not necessary for this failure. This comparison
does not isolate the effect of each internal tracking/smoothing component.

Keep VIDEO mode: switching to IMAGE is not supported as an obstruction fix by
this test. Retain explicit coordinate rejection. Both modes resumed clean pose
predictions after the user returned in one continuous session. This tests raw
pose predictions, not face inference, full posture scoring, alerts, or history.
The outer shoulder/clothing edge and joint can differ, and no stored frames
independently verify the user's physical framing across all samples. Physical
obstruction rejection remains unresolved; no detector is claimed fixed.

Automated suite after adding the comparison tool: 227 passing tests, including
identical-image input, independent result recording, continuous model lifetime,
phase completion/cancellation, and partial initialization cleanup.
