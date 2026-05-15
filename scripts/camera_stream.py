import time
import cv2
import os
import numpy as np


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
                    cv2.rectangle(frame, (x, y), (x + fw, y + fh), (0, 255, 0), 2)

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