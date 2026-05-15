import time
import cv2
import os
import numpy as np
import json


def load_detection_size(settings_path: str, default_size: int = 80) -> int:
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        size = int(data.get("detection_size", default_size)) if isinstance(data, dict) else default_size
    except Exception:
        size = default_size

    return max(1, min(1000, size))


def face_size_range(target_size: int, tolerance: float = 0.20):
    target = max(1, int(target_size))
    delta = max(1, int(round(target * float(tolerance))))
    return max(1, target - delta), target + delta


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


def open_preview_camera(cam_index=0, width=640, height=480, fps=15):
    cap = cv2.VideoCapture(cam_index, cv2.CAP_V4L2)

    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        print("[INFO] Preview camera geopend via V4L2.", flush=True)
        return cap

    cap = cv2.VideoCapture(cam_index)

    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        print("[INFO] Preview camera geopend via standaard OpenCV backend.", flush=True)

    return cap


def generate_camera_frames(
    cam_index=0,
    width=640,
    height=480,
    fps=15,
    smartvision=False,
    preview_opacity=0.08,
):
    cap = None
    camera_deadline = time.time() + 20.0

    while time.time() < camera_deadline:
        cap = open_preview_camera(cam_index, width, height, fps)

        if cap is not None and cap.isOpened():
            break

        if cap is not None:
            cap.release()

        time.sleep(0.5)

    if cap is None or not cap.isOpened():
        print("[FOUT] Preview camera kon niet geopend worden.", flush=True)
        return

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yunet_path = os.path.join(BASE_DIR, "models", "face_detection_yunet_2023mar.onnx")
    settings_path = os.path.join(BASE_DIR, "settings.json")

    try:
        h, w = height, width
        detector = cv2.FaceDetectorYN.create(
            yunet_path,
            "",
            (w, h),
            0.9,  # score_th
            0.3,  # nms_th
            5000,  # topk
        )

        sface_path = os.path.join(BASE_DIR, "models", "face_recognition_sface_2021dec.onnx")
        recognizer = cv2.FaceRecognizerSF.create(sface_path, "")

        known_dir = os.path.join(BASE_DIR, "known")
        known = load_known(known_dir)

        while True:
            ok, frame = cap.read()

            if not ok or frame is None:
                time.sleep(0.1)
                continue

            frame = cv2.resize(frame, (width, height))
            display_frame = frame

            if smartvision:
                black = np.zeros_like(frame)
                opacity = max(0.0, min(1.0, float(preview_opacity)))
                display_frame = cv2.addWeighted(frame, opacity, black, 1.0 - opacity, 0.0)

            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            detection_size = load_detection_size(settings_path)
            min_face_size, max_face_size = face_size_range(detection_size)
            if faces is not None:
                for face in faces:
                    x, y, fw, fh = face[:4].astype(int)
                    face_size = min(fw, fh)
                    in_range = min_face_size <= face_size <= max_face_size
                    box_color = (0, 255, 0) if in_range else (0, 0, 255)

                    labels = [f"size: {face_size}px"]
                    if face_size < min_face_size:
                        labels.append("too far")
                    elif face_size > max_face_size:
                        labels.append("too close")

                    aligned = recognizer.alignCrop(frame, face)
                    feat = recognizer.feature(aligned).astype(np.float32)
                    best_name, best_score, second_score = best_match(recognizer, feat, known)

                    threshold = 0.5
                    margin = 0.1
                    confident = (
                        best_name is not None
                        and best_score >= threshold
                        and (best_score - second_score) >= margin
                    )

                    if confident:
                        labels.insert(0, best_name)

                    if smartvision:
                        if confident:
                            font = cv2.FONT_HERSHEY_SIMPLEX
                            font_scale = 1.2
                            thickness = 3
                            text_w, text_h = cv2.getTextSize(best_name, font, font_scale, thickness)[0]
                            name_x = x + ((fw - text_w) // 2)
                            name_x = min(max(0, name_x), max(0, width - text_w))
                            name_y = max(text_h + 8, y - 12)
                            cv2.putText(
                                display_frame,
                                best_name,
                                (name_x, name_y),
                                font,
                                font_scale,
                                (255, 255, 255),
                                thickness,
                                cv2.LINE_AA,
                            )
                        continue

                    cv2.rectangle(display_frame, (x, y), (x + fw, y + fh), box_color, 2)

                    label_y = max(24, y - 10)
                    for label in reversed(labels):
                        cv2.putText(
                            display_frame,
                            label,
                            (x, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            box_color,
                            2,
                        )
                        label_y -= 24

            ok, buffer = cv2.imencode(".jpg", display_frame)

            if not ok:
                continue

            jpg = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            )

    finally:
        cap.release()
        print("[INFO] Preview camera vrijgegeven.", flush=True)
