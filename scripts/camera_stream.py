import time
import cv2


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

    try:
        while True:
            ok, frame = cap.read()

            if not ok or frame is None:
                time.sleep(0.1)
                continue

            frame = cv2.resize(frame, (width, height))

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