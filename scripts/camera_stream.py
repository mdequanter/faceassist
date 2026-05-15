import time
import cv2
import os
import numpy as np


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


def generate_camera_frames(cam_index=0, width=640, height=480, fps=15):
    cap = open_preview_camera(cam_index, width, height, fps)

    if cap is None or not cap.isOpened():
        print("[FOUT] Preview camera kon niet geopend worden.", flush=True)
        return

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yunet_path = os.path.join(BASE_DIR, "models", "face_detection_yunet_2023mar.onnx")

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

            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            if faces is not None:
                for face in faces:
                    x, y, fw, fh = face[:4].astype(int)
                    face_size = min(fw, fh)
                    cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

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

                    labels = [f"size: {face_size}px"]

                    if confident:
                        labels.insert(0, best_name)

                    label_y = max(24, y - 10)
                    for label in reversed(labels):
                        cv2.putText(
                            frame,
                            label,
                            (x, label_y),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                        label_y -= 24

            ok, buffer = cv2.imencode(".jpg", frame)

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
