from flask import Flask, redirect, render_template, request, url_for
import json
import os
import shutil
import subprocess
import threading
import time
import sys
import os




APP_DIR = os.path.dirname(os.path.abspath(__file__))
FACEASSIST_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
SCRIPTS_DIR = os.path.join(FACEASSIST_DIR, "scripts")
SETTINGS_PATH = os.path.join(FACEASSIST_DIR, "settings.json")
RECOGNITION_SCRIPT = os.path.join(FACEASSIST_DIR, "nl_launchv2.py")
DETECTION_CONTROL_PATH = os.environ.get(
    "FACEASSIST_DETECTION_CONTROL",
    os.path.join(FACEASSIST_DIR, "detection_control.json"),
)

SERVICE_NAME = os.environ.get("FACEASSIST_SERVICE", "faceassist.service")
CONFIG_HOST = os.environ.get("CONFIGURATION_HOST", "0.0.0.0")
CONFIG_PORT = int(os.environ.get("CONFIGURATION_PORT", "5050"))

if FACEASSIST_DIR not in sys.path:
    sys.path.insert(0, FACEASSIST_DIR)

from scripts.camera_stream import generate_camera_frames
from scripts.faces import list_known_people_with_photos


app = Flask(__name__)


def _coerce_voice_volume(value, default_value=100):
    try:
        volume = int(value)
    except Exception:
        volume = int(default_value)
    return max(0, min(100, volume))


def _default_voice_volume():
    return _coerce_voice_volume(os.environ.get("VOICE_VOLUME", "100"), 100)


def _default_settings():
    return {
        "voice_volume": _default_voice_volume(),
    }


def load_settings():
    defaults = _default_settings()
    if not os.path.isfile(SETTINGS_PATH):
        return defaults

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception:
        return defaults

    if not isinstance(settings, dict):
        return defaults

    merged = dict(defaults)
    merged.update(settings)
    settings["voice_volume"] = _coerce_voice_volume(
        settings.get("voice_volume", _default_voice_volume()),
        _default_voice_volume(),
    )
    merged["voice_volume"] = settings["voice_volume"]
    return merged


def save_voice_volume(volume):
    settings = load_settings()
    settings["voice_volume"] = _coerce_voice_volume(
        volume,
        settings.get("voice_volume", _default_voice_volume()),
    )

    tmp_path = f"{SETTINGS_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, SETTINGS_PATH)
    return settings["voice_volume"]


def detection_enabled():
    if not os.path.isfile(DETECTION_CONTROL_PATH):
        return True
    try:
        with open(DETECTION_CONTROL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return True
        return bool(data.get("detection_enabled", data.get("enabled", True)))
    except Exception:
        return True


def save_detection_enabled(enabled):
    payload = {
        "detection_enabled": bool(enabled),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    os.makedirs(os.path.dirname(DETECTION_CONTROL_PATH), exist_ok=True)
    tmp_path = f"{DETECTION_CONTROL_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, DETECTION_CONTROL_PATH)
    return payload["detection_enabled"]


def _run_command(cmd, timeout=12):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return False, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return False, "command timed out"
    except Exception as exc:
        return False, str(exc)

    output = (result.stdout or result.stderr or "").strip()
    if result.returncode == 0:
        return True, output
    return False, output or f"exit code {result.returncode}"


def _run_first_success(cmds, timeout=12):
    errors = []
    for cmd in cmds:
        ok, message = _run_command(cmd, timeout=timeout)
        if ok:
            return True, message
        errors.append(f"{' '.join(cmd)}: {message}")
    return False, " | ".join(errors)


def _system_action_commands(action):
    return [
        ["sudo", "-n", "systemctl", action],
        ["systemctl", action],
    ]


def _run_system_action_later(cmds):
    def _worker():
        time.sleep(1.0)
        _run_first_success(cmds, timeout=30)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def service_status():
    status = {
        "service_name": SERVICE_NAME,
        "systemctl_available": shutil.which("systemctl") is not None,
        "load_state": "unknown",
        "active_state": "unknown",
        "sub_state": "unknown",
        "unit_file_state": "unknown",
        "main_pid": "",
        "fragment_path": "",
        "error": "",
    }

    ok, output = _run_command(
        [
            "systemctl",
            "show",
            SERVICE_NAME,
            "--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,FragmentPath",
            "--no-page",
        ],
        timeout=5,
    )
    if not ok:
        status["error"] = output
        return status

    keys = {
        "LoadState": "load_state",
        "ActiveState": "active_state",
        "SubState": "sub_state",
        "UnitFileState": "unit_file_state",
        "MainPID": "main_pid",
        "FragmentPath": "fragment_path",
    }
    for line in output.splitlines():
        key, sep, value = line.partition("=")
        if sep and key in keys:
            status[keys[key]] = value.strip() or "unknown"

    return status


def _redirect_with(message, level="info"):
    return redirect(url_for("control_page", msg=message, level=level))


def _set_detection_and_redirect(enabled, message):
    try:
        save_detection_enabled(enabled)
    except Exception as exc:
        return _redirect_with(f"Detectiestatus opslaan mislukt: {exc}", "error")
    return _redirect_with(message, "ok")


@app.route("/")
def control_page():
    settings = load_settings()
    return render_template(
        "control.html",
        title="Face Assist Configuration",
        msg=request.args.get("msg", ""),
        level=request.args.get("level", "info"),
        settings=settings,
        status=service_status(),
        detection_enabled=detection_enabled(),
        detection_control_path=DETECTION_CONTROL_PATH,
        recognition_script=RECOGNITION_SCRIPT,
        settings_path=SETTINGS_PATH,
    )


@app.route("/camera")
def camera_page():
    return render_template(
        "camera.html",
        title="Camera Preview",
        active_page="camera",
        detection_enabled=detection_enabled(),
    )

@app.route("/aligncamera")
def aligncamera_page():
    return render_template(
        "aligncamera.html",
        title="Align Camera",
        active_page="aligncamera",
        detection_enabled=detection_enabled(),
    )


@app.route("/aligncamera/feed")
def aligncamera_feed():
    return app.response_class(
        generate_aruco_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.route("/camera/feed")
def camera_feed():
    return app.response_class(
        generate_camera_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/faces")
def unknown_page():
    return render_template(
        "faces.html",
        people=list_known_people_with_photos(),
        msg=request.args.get("msg", ""),
        level=request.args.get("level", "info"),
    )


@app.route("/service/start", methods=["POST"])
def start_service():
    return _set_detection_and_redirect(True, "Detectie aangezet. De service blijft lopen.")


@app.route("/service/stop", methods=["POST"])
def stop_service():
    return _set_detection_and_redirect(False, "Detectie gepauzeerd. De service blijft lopen.")


@app.route("/nl-launch/start", methods=["POST"])
def start_nl_launch():
    return _set_detection_and_redirect(True, "Detectie aangezet.")


@app.route("/nl-launch/stop", methods=["POST"])
def stop_nl_launch():
    return _set_detection_and_redirect(False, "Detectie gepauzeerd.")


@app.route("/detection/enable", methods=["POST"])
def enable_detection():
    return _set_detection_and_redirect(True, "Detectie aangezet.")


@app.route("/detection/disable", methods=["POST"])
def disable_detection():

    return _set_detection_and_redirect(False, "Detectie gepauzeerd.")


@app.route("/api/detection/status")
def api_detection_status():
    return {
        "detection_enabled": detection_enabled(),
        "control_file": DETECTION_CONTROL_PATH,
    }


@app.route("/volume", methods=["POST"])
def set_volume():
    try:
        volume = save_voice_volume(request.form.get("voice_volume"))
    except Exception as exc:
        return _redirect_with(f"Volume save failed: {exc}", "error")
    return _redirect_with(f"Voice volume saved at {volume}.", "ok")


@app.route("/reboot", methods=["POST"])
def reboot_system():
    _run_system_action_later(_system_action_commands("reboot"))
    return _redirect_with("Jetson reboot requested.", "ok")

@app.route("/shutdown", methods=["POST"])
def shutdown_system():
    _run_system_action_later(_system_action_commands("poweroff"))
    return _redirect_with("Jetson shutdown requested.", "ok")



if __name__ == "__main__":
    app.run(host=CONFIG_HOST, port=CONFIG_PORT, debug=False)
