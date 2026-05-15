#!/usr/bin/env python3
"""
Headless face recognition with optional unknown-person handling (OpenCV YuNet + SFace)

Behavior:
- The script uses only the local camera through --cam.
- External camera URLs were removed.
- When detection_control.json sets detection_enabled to false, the camera is released with cap.release().
- While detection is disabled, the script keeps running and periodically checks detection_control.json.
- When detection_enabled becomes true again, the local camera is reopened.

TTS (Piper):
- Default voice: nl_BE-nathalie-medium.onnx (+ .json)
"""

import os
import time
import argparse
import urllib.request
import numpy as np
import cv2
import multiprocessing as mp
import signal
import subprocess
import queue as pyqueue
import sys
import json
import re
from datetime import datetime

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAFE_PERSON_RE = re.compile(r"[^A-Za-z0-9_-]+")

DEFAULT_DETECTION_CONTROL_PATH = os.environ.get(
    "FACEASSIST_DETECTION_CONTROL",
    os.path.join(BASE_DIR, "detection_control.json"),
)


# -----------------------------
# Helpers
# -----------------------------

def download_if_missing(url: str, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return

    print(f"[INFO] Downloading: {os.path.basename(path)} ...", flush=True)
    urllib.request.urlretrieve(url, path)
    print(f"[OK] Saved to {path}", flush=True)


def load_known(known_dir: str):
    known = {}

    if not os.path.isdir(known_dir):
        return known

    for fn in os.listdir(known_dir):
        if fn.lower().endswith(".npz"):
            name = os.path.splitext(fn)[0]
            data = np.load(os.path.join(known_dir, fn))
            feats = data["features"].astype(np.float32)
            known[name] = feats

    return known


def largest_face(faces: np.ndarray):
    if faces is None or len(faces) == 0:
        return None

    areas = faces[:, 2] * faces[:, 3]
    return faces[int(np.argmax(areas))]


def normalize_match_feature(feat):
    if feat is None:
        return None

    arr = np.asarray(feat, dtype=np.float32)
    if arr.size == 0:
        return None

    return arr.reshape(1, -1)


def best_match(recognizer, feat, known: dict):
    feat_match = normalize_match_feature(feat)
    if feat_match is None:
        return None, -1.0, -1.0

    scores = []

    for name, feats in known.items():
        best = -1.0

        for f in feats:
            f_match = normalize_match_feature(f)

            if f_match is None or f_match.shape != feat_match.shape:
                continue

            s = float(
                recognizer.match(
                    feat_match,
                    f_match,
                    cv2.FaceRecognizerSF_FR_COSINE,
                )
            )

            if s > best:
                best = s

        if best > -1.0:
            scores.append((name, best))

    if not scores:
        return None, -1.0, -1.0

    scores.sort(key=lambda x: x[1], reverse=True)

    best_name, best_score = scores[0]
    second_score = scores[1][1] if len(scores) > 1 else -1.0

    return best_name, best_score, second_score


def face_direction_en(x: int, w_face: int, frame_w: int) -> str:
    cx = x + (w_face // 2)

    if cx < frame_w / 3:
        return "is on your left"
    if cx > 2 * frame_w / 3:
        return "is on your right"

    return "is in front of you"


def normalize_qr_text(text: str) -> str:
    return " ".join(str(text or "").split())


def limit_tts_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "..."


def decode_qr_codes(qr_detector, frame):
    decoded = []

    if hasattr(qr_detector, "detectAndDecodeMulti"):
        try:
            ok, decoded_info, _, _ = qr_detector.detectAndDecodeMulti(frame)
            if ok:
                decoded.extend(normalize_qr_text(item) for item in decoded_info)
        except Exception:
            pass

    if not any(decoded):
        try:
            text, _, _ = qr_detector.detectAndDecode(frame)
            decoded.append(normalize_qr_text(text))
        except Exception:
            pass

    unique = []
    seen = set()

    for item in decoded:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)

    return unique


def load_settings_json(settings_path: str):
    if not os.path.isfile(settings_path):
        return {}

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def open_camera_linux(cam_index: int, width: int, height: int, fps: int):
    dev = f"/dev/video{cam_index}"

    gst_pipeline = (
        f"v4l2src device={dev} ! "
        f"image/jpeg,width={width},height={height},framerate={fps}/1 ! "
        f"jpegdec ! videoconvert ! appsink drop=true sync=false max-buffers=1"
    )

    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    if cap.isOpened():
        print("[INFO] Camera opened with GStreamer.", flush=True)
        return cap

    cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        print("[INFO] Camera opened with V4L2 (OpenCV).", flush=True)
        return cap

    cap = cv2.VideoCapture(cam_index)
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        print("[INFO] Camera opened with the default backend (OpenCV).", flush=True)
        return cap

    return cap


def str2bool(s: str) -> bool:
    return str(s).strip().lower() in ("1", "true", "yes", "y", "on", "ja", "j")


def sanitize_name(name: str) -> str:
    name = name.strip().replace("/", "_").replace("\\", "_")
    name = name.replace("..", ".")
    return name


def sanitize_person_name(name: str) -> str:
    cleaned = SAFE_PERSON_RE.sub("_", normalize_qr_text(name))
    cleaned = cleaned.strip("_")
    return cleaned or "qr_person"


def unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    n = 1

    while True:
        candidate = f"{base}_{n}{ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1


def ask_input(prompt: str) -> str:
    sys.stdout.write(prompt)
    sys.stdout.flush()
    return input()


# -----------------------------
# Photo snapshot
# -----------------------------

def save_person_snapshot(frame, name: str, out_dir: str = "snapshots") -> str:
    os.makedirs(out_dir, exist_ok=True)

    safe_name = sanitize_name(name) if name else "Unknown"
    ts = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    path = os.path.join(out_dir, f"{safe_name}_{ts}.jpg")

    cv2.imwrite(path, frame)

    return path


# -----------------------------
# Unknown photo storage
# -----------------------------

def save_unknown_photo(frame, face_row, out_dir: str, idx: int) -> str:
    os.makedirs(out_dir, exist_ok=True)

    x, y, fw, fh = face_row[:4].astype(int)
    h, w = frame.shape[:2]

    pad_w = int(fw * 0.15)
    pad_h = int(fh * 0.15)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(w, x + fw + pad_w)
    y2 = min(h, y + fh + pad_h)

    crop = frame[y1:y2, x1:x2]

    if crop is None or crop.size == 0:
        raise RuntimeError("Empty face crop")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(out_dir, f"{ts}_{idx:04d}.jpg")

    cv2.imwrite(path, crop)

    return path


def save_known_qr_photo(frame, face_row, known_dir: str, person: str, idx: int) -> str:
    person_dir = os.path.join(known_dir, person)
    os.makedirs(person_dir, exist_ok=True)

    x, y, fw, fh = face_row[:4].astype(int)
    h, w = frame.shape[:2]

    pad_w = int(fw * 0.15)
    pad_h = int(fh * 0.15)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(w, x + fw + pad_w)
    y2 = min(h, y + fh + pad_h)

    crop = frame[y1:y2, x1:x2]

    if crop is None or crop.size == 0:
        raise RuntimeError("Empty QR face crop")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = unique_path(os.path.join(person_dir, f"{ts}_qr_{idx:04d}.jpg"))

    cv2.imwrite(path, crop)

    return path


def load_npz_features(npz_path: str):
    if not os.path.isfile(npz_path):
        return None

    data = np.load(npz_path, allow_pickle=True)

    keys = list(data.keys())
    key = "features" if "features" in data else (keys[0] if keys else None)

    if key is None:
        return None

    arr = np.asarray(data[key], dtype=np.float32)

    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim > 2:
        arr = arr.reshape(arr.shape[0], -1)

    if arr.ndim != 2 or arr.shape[0] == 0:
        return None

    return arr


def normalize_face_feature(feat):
    if feat is None:
        return None

    arr = np.asarray(feat, dtype=np.float32)

    if arr.size == 0:
        return None

    return arr.reshape(-1)


def append_known_features(known_dir: str, person: str, new_features: list) -> int:
    if not new_features:
        return 0

    normalized = []

    for feat in new_features:
        feat_1d = normalize_face_feature(feat)
        if feat_1d is not None:
            normalized.append(feat_1d)

    if not normalized:
        return 0

    os.makedirs(known_dir, exist_ok=True)

    npz_path = os.path.join(known_dir, f"{person}.npz")
    new_stack = np.stack(normalized, axis=0).astype(np.float32)

    old = load_npz_features(npz_path)

    if old is not None:
        merged = np.concatenate([old, new_stack], axis=0)
    else:
        merged = new_stack

    np.savez_compressed(npz_path, features=merged)

    return int(new_stack.shape[0])


def face_size_range(target_size: int, tolerance: float = 0.20):
    target = max(1, int(target_size))
    delta = max(1, int(round(target * float(tolerance))))
    return max(1, target - delta), target + delta


def play_qr_click(duration_ms: int = 70, frequency: int = 1200, volume: int = 100) -> None:
    try:
        sample_rate = 16000
        sample_count = max(1, int(sample_rate * max(10, duration_ms) / 1000.0))

        t = np.arange(sample_count, dtype=np.float32)
        audio = np.sin((2.0 * np.pi * float(frequency) * t) / sample_rate)

        ramp_len = min(sample_count // 2, int(sample_rate * 0.005))

        if ramp_len > 0:
            ramp = np.linspace(0.0, 1.0, ramp_len, dtype=np.float32)
            audio[:ramp_len] *= ramp
            audio[-ramp_len:] *= ramp[::-1]

        pcm = np.clip(
            audio * 32767.0 * (max(0, min(100, int(volume))) / 100.0),
            -32768,
            32767,
        )

        raw_audio = pcm.astype(np.int16).tobytes()

        result = subprocess.run(
            ["aplay", "-q", "-r", str(sample_rate), "-f", "S16_LE", "-t", "raw", "-"],
            input=raw_audio,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )

        if result.returncode != 0:
            print("\a", end="", flush=True)

    except Exception:
        try:
            print("\a", end="", flush=True)
        except Exception:
            pass


# -----------------------------
# Piper TTS
# -----------------------------

def read_piper_sample_rate(model_path: str, default_rate: int = 22050) -> int:
    json_path = model_path + ".json"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key in ("sample_rate", "audio.sample_rate", "audio_sample_rate"):
            if key in data and isinstance(data[key], int):
                return int(data[key])

        if isinstance(data.get("audio"), dict) and isinstance(data["audio"].get("sample_rate"), int):
            return int(data["audio"]["sample_rate"])

    except Exception:
        pass

    return default_rate


def piper_say(
    text: str,
    model_path: str,
    sample_rate: int,
    length_scale: float = 1.0,
    volume: int = 100,
):
    p1 = subprocess.Popen(
        [
            "/home/jetson/piper/piper",
            "--model",
            model_path,
            "--output_raw",
            "--length_scale",
            str(length_scale),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    try:
        raw_audio, _ = p1.communicate(input=(text + "\n").encode("utf-8"), timeout=60)
    except subprocess.TimeoutExpired:
        p1.kill()
        return

    if not raw_audio:
        return

    vol = max(0, min(100, int(volume)))

    if vol < 100:
        pcm = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32)
        pcm *= vol / 100.0
        np.clip(pcm, -32768, 32767, out=pcm)
        raw_audio = pcm.astype(np.int16).tobytes()

    p2 = subprocess.Popen(
        ["aplay", "-r", str(sample_rate), "-f", "S16_LE", "-t", "raw", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        p2.communicate(input=raw_audio, timeout=60)
    except subprocess.TimeoutExpired:
        p2.kill()


def tts_worker_loop(tts_queue, stop_event, args, done_queue=None, voice_volume_value=None):
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        subprocess.run(["piper", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        print("[WARNING] 'piper' was not found in PATH.", flush=True)
        return

    model_path = os.path.expanduser(args.piper_model)

    if not os.path.exists(model_path):
        print(f"[WARNING] Piper model not found: {model_path}", flush=True)
        return

    sample_rate = args.piper_rate

    if args.piper_rate_auto:
        sample_rate = read_piper_sample_rate(model_path, default_rate=args.piper_rate)

    while not stop_event.is_set():
        try:
            msg = tts_queue.get(timeout=0.1)
        except pyqueue.Empty:
            continue

        if msg is None:
            break

        done_token = None

        if isinstance(msg, dict):
            text = str(msg.get("text", "")).strip()
            done_token = msg.get("done_token")
        else:
            text = str(msg).strip()

        if not text:
            if done_token and done_queue is not None:
                try:
                    done_queue.put_nowait(done_token)
                except pyqueue.Full:
                    pass
            continue


        try:
            volume = voice_volume_value.value if voice_volume_value is not None else args.voice_volume
            piper_say(
                text,
                model_path=model_path,
                sample_rate=sample_rate,
                length_scale=args.piper_length_scale,
                volume=volume,
            )
        except Exception:
            pass
        finally:
            if done_token and done_queue is not None:
                try:
                    done_queue.put_nowait(done_token)
                except pyqueue.Full:
                    pass


def tts_enqueue(tts_queue, text: str, done_token=None) -> bool:
    if tts_queue is None:
        return False

    msg = {"text": text, "done_token": done_token} if done_token else text

    try:
        tts_queue.put_nowait(msg)
        return True
    except pyqueue.Full:
        return False


class DetectionControl:
    def __init__(self, path: str, poll_interval: float = 10.0, default_enabled: bool = True):
        self.path = os.path.abspath(path) if path else ""
        self.poll_interval = max(0.1, float(poll_interval))
        self.default_enabled = bool(default_enabled)
        self._last_checked = 0.0
        self._enabled = bool(default_enabled)

    def enabled(self) -> bool:
        now = time.time()

        if (now - self._last_checked) < self.poll_interval:
            return self._enabled

        self._last_checked = now

        if not self.path or not os.path.isfile(self.path):
            self._enabled = self.default_enabled
            return self._enabled

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                self._enabled = bool(
                    data.get(
                        "detection_enabled",
                        data.get("enabled", self.default_enabled),
                    )
                )
            else:
                self._enabled = self.default_enabled

        except Exception as exc:
            print(f"[WARNING] Failed to read detection control file: {exc}", flush=True)
            self._enabled = self.default_enabled

        return self._enabled


def drain_done_queue(done_queue) -> set:
    tokens = set()

    if done_queue is None:
        return tokens

    while True:
        try:
            tokens.add(done_queue.get_nowait())
        except pyqueue.Empty:
            break

    return tokens


# -----------------------------
# Snapshot storage
# -----------------------------

def save_snapshot(frame, out_dir: str, tag: str) -> str:
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_tag = sanitize_name(tag) if tag else "unknown"
    path = os.path.join(out_dir, f"{ts}_{safe_tag}.jpg")

    cv2.imwrite(path, frame)

    return path


# -----------------------------
# Main
# -----------------------------

def main():
    settings_path = os.path.join(BASE_DIR, "settings.json")
    settings = load_settings_json(settings_path)

    ap = argparse.ArgumentParser()

    # Camera and detection
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--infer_every", type=int, default=2)

    ap.add_argument("--min_face", type=int, default=50)
    ap.add_argument("--score_th", type=float, default=0.9)
    ap.add_argument("--nms_th", type=float, default=0.3)
    ap.add_argument("--topk", type=int, default=5000)

    # Recognition
    ap.add_argument("--threshold", type=float, default=0.60)
    ap.add_argument("--margin", type=float, default=0.06)

    # Entry / leave
    ap.add_argument("--lost_timeout", type=float, default=1.0)
    ap.add_argument("--enter_confirm_frames", type=int, default=3)
    ap.add_argument("--reannounce_after", type=float, default=6.0)

    # Unknown-person behavior
    ap.add_argument(
        "--unknown_seconds",
        type=float,
        default=5.0,
        help="(legacy) If an unknown face stays visible this long, ask to save it.",
    )
    ap.add_argument(
        "--unknown_confirm_frames",
        type=int,
        default=5,
        help="Number of consecutive 'unknown' frames before starting.",
    )
    ap.add_argument(
        "--cooldown_after_unknown",
        type=float,
        default=300.0,
        help="Wait this long after handling an unknown person.",
    )

    ap.add_argument(
        "--unknown_capture_interval",
        type=float,
        default=0.5,
        help="(legacy) During unknown handling: take a feature snapshot every N seconds.",
    )
    ap.add_argument(
        "--unknown_max_snaps",
        type=int,
        default=60,
        help="(legacy) Maximum number of feature snapshots to keep.",
    )

    # Storage
    ap.add_argument(
        "--known",
        type=str,
        default=os.path.join(BASE_DIR, "known"),
        help="Directory with .npz identities",
    )
    ap.add_argument(
        "--min_save_samples",
        type=int,
        default=20,
        help="(legacy) Do not save if there are too few snapshots",
    )

    # Photos
    ap.add_argument(
        "--unknown_photos",
        type=str,
        default="unknown_photos",
        help="(legacy) Directory for optionally saving a JPG",
    )
    ap.add_argument(
        "--save_unknown_snapshot",
        action="store_true",
        help="(legacy) Also save one JPG when saving a new person.",
    )

    # QR-code scanner
    ap.add_argument("--no_qr", action="store_true", help="Disable the QR-code scanner.")
    ap.add_argument("--qr_every", type=int, default=5, help="Scan for QR codes every N frames.")
    ap.add_argument(
        "--qr_cooldown",
        type=float,
        default=8.0,
        help="Seconds before the same QR code is announced again.",
    )
    ap.add_argument(
        "--qr_max_chars",
        type=int,
        default=500,
        help="Maximum number of QR characters for TTS. Use 0 for unlimited.",
    )
    ap.add_argument(
        "--qr_prefix",
        type=str,
        default=(
            "Thank you for registering. "
            "Stand in the doorway for a few seconds with your face toward the camera. "
            "You will be registered under the name: "
        ),
        help="Text spoken before the QR content.",
    )
    ap.add_argument(
        "--detection_size",
        type=int,
        default=settings.get("detection_size", 80),
        help="Target size in pixels for QR registration; photos are taken within +/- 20 percent.",
    )
    ap.add_argument(
        "--qr_min_face",
        type=int,
        default=None,
        help="Alias voor --detection_size.",
    )
    ap.add_argument(
        "--qr_photo_count",
        type=int,
        default=5,
        help="Number of photos to save in known/<QR-name>/ once exactly one face is at the correct distance.",
    )
    ap.add_argument(
        "--qr_capture_interval",
        type=float,
        default=0.5,
        help="Time between QR registration photos in seconds.",
    )
    ap.add_argument(
        "--no_qr_clicks",
        action="store_true",
        help="Do not play a short click/beep at capture start or for each QR photo.",
    )

    # Piper TTS
    ap.add_argument("--no_tts", action="store_true")
    ap.add_argument("--speak", type=str, default="True")
    ap.add_argument(
        "--piper_model",
        type=str,
        default="/home/jetson/faceassist/voices/nl_BE-nathalie-medium.onnx",
    )
    ap.add_argument("--piper_rate", type=int, default=22050)
    ap.add_argument("--piper_rate_auto", action="store_true")
    ap.add_argument("--piper_length_scale", type=float, default=1.0)
    ap.add_argument("--voice_volume", type=int, default=settings.get("voice_volume", 20))
    ap.add_argument("--tts_queue_size", type=int, default=20)

    # Detection control
    ap.add_argument(
        "--control_file",
        type=str,
        default=DEFAULT_DETECTION_CONTROL_PATH,
        help="JSON file used to enable/disable detection without stopping the process.",
    )
    ap.add_argument(
        "--control_poll_interval",
        type=float,
        default=10.0,
        help="Seconds between detection-control file checks.",
    )

    args = ap.parse_args()

    args.voice_volume = max(0, min(100, int(args.voice_volume)))
    args.qr_every = max(1, int(args.qr_every))
    args.qr_max_chars = max(0, int(args.qr_max_chars))
    args.detection_size = max(1, min(1000, int(args.detection_size)))
    if args.qr_min_face is not None:
        args.detection_size = max(1, min(1000, int(args.qr_min_face)))
    args.qr_min_face = args.detection_size
    args.qr_photo_count = max(1, int(args.qr_photo_count))
    args.qr_capture_interval = max(0.0, float(args.qr_capture_interval))
    args.control_poll_interval = max(0.1, float(args.control_poll_interval))

    yunet_path = os.path.join("models", "face_detection_yunet_2023mar.onnx")
    sface_path = os.path.join("models", "face_recognition_sface_2021dec.onnx")

    download_if_missing(YUNET_URL, yunet_path)
    download_if_missing(SFACE_URL, sface_path)

    os.makedirs(args.known, exist_ok=True)

    # TTS
    stop_event = mp.Event()
    tts_queue = None
    tts_done_queue = None
    tts_proc = None
    voice_volume_value = mp.Value("i", args.voice_volume)

    speak_enabled = (not args.no_tts) and str2bool(args.speak)

    if speak_enabled:
        tts_queue = mp.Queue(maxsize=args.tts_queue_size)
        tts_done_queue = mp.Queue(maxsize=args.tts_queue_size)

        tts_proc = mp.Process(
            target=tts_worker_loop,
            args=(tts_queue, stop_event, args, tts_done_queue, voice_volume_value),
            daemon=True,
        )
        tts_proc.start()

        if args.no_qr:
            tts_enqueue(tts_queue, "Face recognition has started.")
        else:
            tts_enqueue(tts_queue, "Face recognition and QR scanner have started.")

    cap = None

    # Camera
    cap = open_camera_linux(args.cam, args.width, args.height, args.fps)

    if cap is None or not cap.isOpened():
        print("[ERROR] Cannot open camera.", flush=True)
        stop_event.set()

        if tts_queue is not None:
            try:
                tts_queue.put_nowait(None)
            except Exception:
                pass

        return

    ok, frame = cap.read()

    if not ok or frame is None:
        print("[ERROR] Cannot read first frame.", flush=True)

        if cap is not None:
            cap.release()
            cap = None

        return

    h, w = frame.shape[:2]

    detector = cv2.FaceDetectorYN.create(
        yunet_path,
        "",
        (w, h),
        args.score_th,
        args.nms_th,
        args.topk,
    )
    recognizer = cv2.FaceRecognizerSF.create(sface_path, "")

    qr_detector = None
    qr_enabled = not args.no_qr

    if qr_enabled:
        try:
            qr_detector = cv2.QRCodeDetector()
            print("[INFO] QR scanner is active.", flush=True)
        except Exception as e:
            qr_enabled = False
            print(f"[WARNING] QR scanner could not start: {e}", flush=True)

    known = load_known(args.known)

    if known:
        print("[INFO] Known:", ", ".join(sorted(known.keys())), flush=True)

        if speak_enabled:
            tts_enqueue(tts_queue, f"{len(known)} people loaded.")
    else:
        print(f"[WARNING] No known identities in '{args.known}'.", flush=True)

        if speak_enabled:
            tts_enqueue(tts_queue, "I do not know anyone yet.")

    # Entry/leave state
    present = False
    present_name = None
    last_seen = 0.0

    consec_needed = args.enter_confirm_frames
    consec_count = 0
    candidate_name = None
    last_announced_at = {}

    # Unknown state
    unknown_consec = 0
    unknown_started_at = None
    last_unknown_handled_at = 0.0

    unknown_dir = "unknown"
    unknown_photo_count = 0
    unknown_photo_interval = 60
    unknown_last_photo_at = 0.0

    last_person_photo_at = {}
    person_photo_cooldown = 300.0

    # QR-code state
    last_qr_announced_at = {}
    qr_registration = None
    qr_registration_seq = 0

    frame_id = 0

    detection_control = DetectionControl(
        args.control_file,
        args.control_poll_interval,
        default_enabled=True,
    )

    settings_check_interval = args.control_poll_interval
    last_settings_check = time.time()

    detection_paused = False

    print(f"[INFO] Detection control file: {detection_control.path}", flush=True)
    print(f"[INFO] Detection control poll interval: {args.control_poll_interval:.1f}s", flush=True)
    print(f"[INFO] Settings reload interval: {settings_check_interval:.1f}s", flush=True)
    print("[INFO] Headless mode is active. Press Ctrl+C to stop.", flush=True)

    try:
        while True:
            now = time.time()
            if now - last_settings_check >= settings_check_interval:
                last_settings_check = now
                current_settings = load_settings_json(settings_path)
                if "voice_volume" in current_settings:
                    try:
                        new_volume = max(0, min(100, int(current_settings["voice_volume"])))
                        args.voice_volume = new_volume
                        voice_volume_value.value = new_volume
                        print(f"[INFO] Settings reloaded: volume={args.voice_volume}", flush=True)
                    except Exception:
                        pass
                if "detection_size" in current_settings:
                    try:
                        new_detection_size = max(1, min(1000, int(current_settings["detection_size"])))
                        args.detection_size = new_detection_size
                        args.qr_min_face = new_detection_size
                        print(
                            f"[INFO] Settings reloaded: detection_size={args.detection_size}px",
                            flush=True,
                        )
                    except Exception:
                        pass

            if not detection_control.enabled():
                if not detection_paused:
                    print(
                        "[INFO] Detection paused by configuration. Releasing camera.",
                        flush=True,
                    )

                    if speak_enabled and tts_queue is not None:
                        tts_enqueue(tts_queue, "Detection paused.")

                    if cap is not None:
                        cap.release()
                        cap = None
                        print("[INFO] Camera released.", flush=True)

                    present = False
                    present_name = None
                    last_seen = 0.0
                    consec_count = 0
                    candidate_name = None
                    unknown_consec = 0
                    unknown_started_at = None
                    unknown_dir = "unknown"
                    unknown_photo_count = 0
                    unknown_last_photo_at = 0.0
                    qr_registration = None
                    detection_paused = True

                drain_done_queue(tts_done_queue)
                time.sleep(args.control_poll_interval)
                continue

            if detection_paused:
                print(
                    "[INFO] Detection resumed by configuration. Reopening camera.",
                    flush=True,
                )

                if speak_enabled and tts_queue is not None:
                    tts_enqueue(tts_queue, "Detection resumed.")

                cap = open_camera_linux(args.cam, args.width, args.height, args.fps)

                if cap is None or not cap.isOpened():
                    print("[ERROR] Cannot reopen camera.", flush=True)

                    if cap is not None:
                        cap.release()
                        cap = None

                    time.sleep(args.control_poll_interval)
                    continue

                ok, frame = cap.read()

                if not ok or frame is None:
                    print("[ERROR] Cannot read first frame after resuming.", flush=True)

                    cap.release()
                    cap = None

                    time.sleep(args.control_poll_interval)
                    continue

                h, w = frame.shape[:2]
                detector.setInputSize((w, h))

                detection_paused = False

            if cap is None or not cap.isOpened():
                print("[WARNING] Camera is unavailable. Retrying.", flush=True)
                time.sleep(args.control_poll_interval)
                continue

            ok, frame = cap.read()

            if not ok or frame is None:
                time.sleep(0.1)
                continue

            frame_id += 1
            now = time.time()

            tts_done_tokens = drain_done_queue(tts_done_queue)

            if qr_registration is not None:
                if qr_registration["state"] == "waiting_speech":
                    if qr_registration.get("speech_token") in tts_done_tokens:
                        qr_registration["state"] = "waiting_face"

                        print(
                            f"[QR] QR text spoken. Waiting for 1 face at the correct distance for {qr_registration['person']}.",
                            flush=True,
                        )

                    elif speak_enabled and tts_proc is not None and not tts_proc.is_alive():
                        qr_registration["state"] = "waiting_face"

                        print(
                            "[WARNING] TTS process stopped; waiting for a face at the correct distance.",
                            flush=True,
                        )

            if qr_enabled and qr_registration is None and qr_detector is not None and frame_id % args.qr_every == 0:
                for qr_text in decode_qr_codes(qr_detector, frame):
                    last_qr = last_qr_announced_at.get(qr_text, 0.0)

                    if now - last_qr < args.qr_cooldown:
                        continue

                    last_qr_announced_at[qr_text] = now

                    qr_name = sanitize_person_name(qr_text)

                    print(f"[QR] {qr_text}", flush=True)
                    print(f"[QR] Registration directory: {os.path.join(args.known, qr_name)}", flush=True)

                    qr_registration_seq += 1
                    speech_token = f"qr-speech:{qr_registration_seq}"

                    qr_registration = {
                        "id": qr_registration_seq,
                        "raw_text": qr_text,
                        "person": qr_name,
                        "state": "waiting_speech",
                        "speech_token": speech_token,
                        "captured": 0,
                        "features_added": 0,
                        "last_capture_at": 0.0,
                        "last_status_at": 0.0,
                    }

                    if speak_enabled:
                        tts_text = limit_tts_text(qr_text, args.qr_max_chars)

                        spoken = tts_enqueue(
                            tts_queue,
                            f"{args.qr_prefix} {tts_text}".strip(),
                            done_token=speech_token,
                        )

                        if not spoken:
                            qr_registration["state"] = "waiting_face"
                            print(
                                "[WARNING] TTS queue is full; waiting for a face at the correct distance.",
                                flush=True,
                            )
                    else:
                        qr_registration["state"] = "waiting_face"
                        print("[QR] TTS is disabled. Waiting for 1 face at the correct distance.", flush=True)

                    break

            if (
                qr_registration is not None
                and qr_registration["state"] not in ("waiting_face", "capturing")
            ):
                continue

            if frame_id % args.infer_every != 0:
                continue

            detector.setInputSize((w, h))

            _, faces = detector.detect(frame)
            face_count = 0 if faces is None else len(faces)
            face = largest_face(faces)

            if qr_registration is not None and qr_registration["state"] == "waiting_face":
                if face_count != 1:
                    if now - qr_registration.get("last_status_at", 0.0) >= 1.0:
                        print(
                            f"[QR] Waiting for exactly 1 face for {qr_registration['person']} "
                            f"(detected: {face_count}).",
                            flush=True,
                        )
                        qr_registration["last_status_at"] = now

                    continue

                x, y, fw, fh = face[:4].astype(int)
                face_size = min(fw, fh)
                min_face_size, max_face_size = face_size_range(args.detection_size)

                print(f"[QR] Face detected for {qr_registration['person']} ({face_size}px).", flush=True)

                if face_size < min_face_size or face_size > max_face_size:
                    if now - qr_registration.get("last_status_at", 0.0) >= 1.0:
                        print(
                            f"[QR] Face is not at the correct distance for {qr_registration['person']} "
                            f"({face_size}px, target {args.detection_size}px, "
                            f"range {min_face_size}-{max_face_size}px).",
                            flush=True,
                        )
                        qr_registration["last_status_at"] = now

                    continue

                qr_registration["state"] = "capturing"
                qr_registration["last_capture_at"] = 0.0

                print(
                    f"[QR] 1 face is at the correct distance ({face_size}px). Taking photos for "
                    f"{qr_registration['person']}.",
                    flush=True,
                )

                if not args.no_qr_clicks:
                    play_qr_click(volume=args.voice_volume)

            if qr_registration is not None and qr_registration["state"] == "capturing" and face_count != 1:
                if now - qr_registration.get("last_status_at", 0.0) >= 1.0:
                    print(
                        f"[QR] Photos paused: exactly 1 face is required for "
                        f"{qr_registration['person']} (detected: {face_count}).",
                        flush=True,
                    )
                    qr_registration["last_status_at"] = now

                continue

            if face is None:
                if qr_registration is not None and qr_registration["state"] == "capturing":
                    if now - qr_registration.get("last_status_at", 0.0) >= 1.0:
                        print(
                            f"[QR] Waiting for a face for {qr_registration['person']}...",
                            flush=True,
                        )
                        qr_registration["last_status_at"] = now

                    continue

                if present and now - last_seen >= args.lost_timeout:
                    print(f"[INFO] {present_name} left the frame.", flush=True)

                    present = False
                    present_name = None
                    consec_count = 0
                    candidate_name = None

                unknown_consec = 0
                unknown_started_at = None
                unknown_dir = "unknown"
                unknown_photo_count = 0
                unknown_last_photo_at = 0.0

                continue

            x, y, fw, fh = face[:4].astype(int)

            if qr_registration is not None and qr_registration["state"] == "capturing":
                face_size = min(fw, fh)
                min_face_size, max_face_size = face_size_range(args.detection_size)

                if face_size < min_face_size or face_size > max_face_size:
                    if now - qr_registration.get("last_status_at", 0.0) >= 1.0:
                        print(
                            f"[QR] Photos paused: face is not at the correct distance for "
                            f"{qr_registration['person']} ({face_size}px, target {args.detection_size}px, "
                            f"range {min_face_size}-{max_face_size}px).",
                            flush=True,
                        )
                        qr_registration["last_status_at"] = now

                    continue

            else:
                face_size = min(fw, fh)
                min_face_size, max_face_size = face_size_range(args.detection_size)

                if face_size < min_face_size or face_size > max_face_size:
                    if present and now - last_seen >= args.lost_timeout:
                        print(f"[INFO] {present_name} left the frame.", flush=True)

                        present = False
                        present_name = None

                    unknown_consec = 0
                    unknown_started_at = None
                    unknown_dir = "unknown"
                    unknown_photo_count = 0
                    unknown_last_photo_at = 0.0

                    consec_count = 0
                    candidate_name = None

                    continue


            if qr_registration is not None and qr_registration["state"] == "capturing":
                if args.qr_capture_interval <= 0 or now - qr_registration["last_capture_at"] >= args.qr_capture_interval:
                    idx = qr_registration["captured"] + 1

                    try:
                        p = save_known_qr_photo(frame, face, args.known, qr_registration["person"], idx)

                        added_now = 0

                        try:
                            aligned_qr = recognizer.alignCrop(frame, face)
                            feat_qr = recognizer.feature(aligned_qr).astype(np.float32)

                            added_now = append_known_features(
                                args.known,
                                qr_registration["person"],
                                [feat_qr],
                            )

                            qr_registration["features_added"] += added_now

                            if added_now > 0:
                                known = load_known(args.known)

                        except Exception as e:
                            print(f"[WARNING] QR feature extraction failed: {e}", flush=True)

                        qr_registration["captured"] = idx
                        qr_registration["last_capture_at"] = now

                        if not args.no_qr_clicks:
                            play_qr_click(volume=args.voice_volume)

                        print(
                            f"[OK] QR photo {idx}/{args.qr_photo_count}: {p} "
                            f"({added_now} feature added)",
                            flush=True,
                        )

                    except Exception as e:
                        qr_registration["last_capture_at"] = now
                        print(f"[WARNING] Failed to save QR photo: {e}", flush=True)

                    if qr_registration["captured"] >= args.qr_photo_count:
                        known = load_known(args.known)

                        print(
                            f"[INFO] QR registration complete for {qr_registration['person']}: "
                            f"{qr_registration['captured']} photo(s), "
                            f"{qr_registration['features_added']} feature(s).",
                            flush=True,
                        )

                        if speak_enabled:
                            tts_enqueue(tts_queue, f"Registration complete for {qr_registration['person']}")

                        last_qr_announced_at[qr_registration["raw_text"]] = time.time()

                        qr_registration = None

                continue

            aligned = recognizer.alignCrop(frame, face)
            feat = recognizer.feature(aligned).astype(np.float32)

            if known:
                best_name, best_score, second_score = best_match(recognizer, feat, known)
            else:
                best_name, best_score, second_score = None, -1.0, -1.0

            confident = (
                best_name is not None
                and best_score >= args.threshold
                and (best_score - second_score) >= args.margin
            )

            # -------------------------
            # UNKNOWN
            # -------------------------
            if not confident:
                if present and now - last_seen >= args.lost_timeout:
                    print(f"[INFO] {present_name} left the frame.", flush=True)

                    present = False
                    present_name = None
                    consec_count = 0
                    candidate_name = None

                if now - last_unknown_handled_at < args.cooldown_after_unknown:
                    unknown_consec = 0
                    unknown_started_at = None
                    unknown_dir = "unknown"
                    unknown_photo_count = 0
                    unknown_last_photo_at = 0.0

                    continue

                unknown_consec += 1

                if unknown_consec < args.unknown_confirm_frames:
                    continue

                if unknown_started_at is None:
                    unknown_started_at = now
                    unknown_photo_count = 0
                    unknown_last_photo_at = 0.0

                    os.makedirs(unknown_dir, exist_ok=True)

                    print(f"[INFO] Unknown person detected -> directory: {unknown_dir}", flush=True)

                # This photo storage is intentionally still disabled, as in the original code.
                # if unknown_dir is not None:
                #     if now - unknown_last_photo_at >= unknown_photo_interval:
                #         unknown_photo_count += 1
                #         p = save_unknown_photo(frame, face, unknown_dir, unknown_photo_count)
                #         unknown_last_photo_at = now
                #         print(f"[OK] Unknown photo {unknown_photo_count}/20: {p}", flush=True)

                if unknown_photo_count >= 20:
                    print(f"[INFO] Unknown session complete (20 photos) -> {unknown_dir}", flush=True)

                    last_unknown_handled_at = time.time()

                    unknown_consec = 0
                    unknown_started_at = None
                    unknown_dir = "unknown"
                    unknown_photo_count = 0
                    unknown_last_photo_at = 0.0

                continue

            # -------------------------
            # KNOWN
            # -------------------------
            last_seen = now

            unknown_consec = 0
            unknown_started_at = None
            unknown_dir = "unknown"
            unknown_photo_count = 0
            unknown_last_photo_at = 0.0

            if present and best_name == present_name:
                continue

            if candidate_name == best_name:
                consec_count += 1
            else:
                candidate_name = best_name
                consec_count = 1

            if consec_count < consec_needed:
                continue

            last_spoke = last_announced_at.get(candidate_name, 0.0)

            if now - last_spoke < args.reannounce_after:
                present = True
                present_name = candidate_name
                consec_count = 0
                candidate_name = None

                continue

            present = True
            present_name = candidate_name

            last_announced_at[present_name] = now
            direction = face_direction_en(x, fw, w)

            print(
                f"[INFO] ENTERED: {present_name} {direction} "
                f"(score={best_score:.2f}, second={second_score:.2f})",
                flush=True,
            )

            if best_score > args.threshold:
                last_t = last_person_photo_at.get(present_name, 0.0)

                if now - last_t >= person_photo_cooldown:
                    # p = save_person_snapshot(frame, present_name, out_dir="snapshots")
                    # last_person_photo_at[present_name] = now
                    # print("[OK] Snapshot saved:", p, flush=True)

                    if speak_enabled:
                        tts_enqueue(tts_queue, f"Hello {present_name}")

                consec_count = 0
                candidate_name = None

    except KeyboardInterrupt:
        print("\n[INFO] Stopping...", flush=True)

    finally:
        if cap is not None:
            cap.release()

        stop_event.set()

        if tts_queue is not None:
            try:
                tts_queue.put_nowait(None)
            except Exception:
                pass

        if tts_proc is not None:
            tts_proc.join(timeout=1.0)

            if tts_proc.is_alive():
                tts_proc.terminate()
                tts_proc.join()


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
