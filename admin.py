from flask import Flask, redirect, render_template, request, url_for, send_from_directory, session
import json
import os
import shutil
import subprocess
import threading
import time
import sys
import secrets
import csv
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash



APP_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_DIR = os.path.join(APP_DIR, "scripts")
SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
DETECTION_CONTROL_PATH = os.path.join(APP_DIR, "detection_control.json")
RECOGNITION_SCRIPT = os.path.join(SCRIPTS_DIR, "launch.py")
DETECTED_FACES_LOG_PATH = os.path.join(APP_DIR, "logs", "detectedFaces.csv")


SERVICE_NAME = os.environ.get("FACEASSIST_SERVICE", "faceassist.service")
CONFIG_HOST = os.environ.get("CONFIGURATION_HOST", "0.0.0.0")
CONFIG_PORT = int(os.environ.get("CONFIGURATION_PORT", "5050"))

from scripts.camera_stream import generate_camera_frames
from scripts.faces import list_known_people_with_photos


app = Flask(__name__)
app.secret_key = os.environ.get("FACEASSIST_SECRET_KEY", "faceassist-admin-session")


def _coerce_voice_volume(value, default_value=100):
    try:
        volume = int(value)
    except Exception:
        volume = int(default_value)
    return max(0, min(100, volume))


def _coerce_detection_size(value, default_value=80):
    try:
        size = int(value)
    except Exception:
        size = int(default_value)
    return max(1, min(1000, size))


def _default_voice_volume():
    return _coerce_voice_volume(os.environ.get("VOICE_VOLUME", "100"), 100)


def _default_detection_size():
    return _coerce_detection_size(os.environ.get("DETECTION_SIZE", "80"), 80)


def _default_settings():
    return {
        "voice_volume": _default_voice_volume(),
        "detection_size": _default_detection_size(),
    }


def _write_settings(settings):
    tmp_path = f"{SETTINGS_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, SETTINGS_PATH)


def _coerce_bool(value, default_value=False):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "y", "on", "ja", "j"):
        return True
    if text in ("0", "false", "no", "n", "off", "nee", "niet"):
        return False

    return bool(default_value)


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
    settings["detection_size"] = _coerce_detection_size(
        settings.get("detection_size", _default_detection_size()),
        _default_detection_size(),
    )
    merged["voice_volume"] = settings["voice_volume"]
    merged["detection_size"] = settings["detection_size"]
    return merged


def ensure_admin_password_hash():
    settings = load_settings()
    if settings.get("admin_password_hash"):
        return

    password = os.environ.get("FACEASSIST_ADMIN_PASSWORD", "admin")
    settings["admin_password_hash"] = generate_password_hash(password)
    _write_settings(settings)


def ensure_admin_session_secret():
    settings = load_settings()
    session_secret = settings.get("admin_session_secret")
    if session_secret:
        return session_secret

    session_secret = secrets.token_urlsafe(32)
    settings["admin_session_secret"] = session_secret
    _write_settings(settings)
    return session_secret


def save_admin_password(password):
    settings = load_settings()
    settings["admin_password_hash"] = generate_password_hash(password)
    _write_settings(settings)


def verify_admin_password(password):
    password_hash = load_settings().get("admin_password_hash", "")
    return bool(password_hash) and check_password_hash(password_hash, password or "")


def save_voice_volume(volume):
    settings = load_settings()
    settings["voice_volume"] = _coerce_voice_volume(
        volume,
        settings.get("voice_volume", _default_voice_volume()),
    )

    _write_settings(settings)
    return settings["voice_volume"]


def save_detection_size(size):
    settings = load_settings()
    settings["detection_size"] = _coerce_detection_size(
        size,
        settings.get("detection_size", _default_detection_size()),
    )

    _write_settings(settings)
    return settings["detection_size"]


def detection_enabled():
    if not os.path.isfile(DETECTION_CONTROL_PATH):
        return True
    try:
        with open(DETECTION_CONTROL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return True
        return _coerce_bool(
            data.get("detection_enabled", data.get("enabled", True)),
            True,
        )
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


def _empty_detected_faces_log():
    os.makedirs(os.path.dirname(DETECTED_FACES_LOG_PATH), exist_ok=True)
    with open(DETECTED_FACES_LOG_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "Name", "size"])


def _parse_visit_time(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def read_detected_faces_log():
    if not os.path.isfile(DETECTED_FACES_LOG_PATH):
        return []

    visits = []
    with open(DETECTED_FACES_LOG_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            if not row:
                continue
            visits.append(
                {
                    "time": (row.get("time") or "").strip(),
                    "name": (row.get("Name") or row.get("name") or "").strip(),
                    "size": (row.get("size") or "").strip(),
                }
            )

    visits.reverse()
    return visits


def prune_detected_faces_log(days=31):
    cutoff = datetime.now() - timedelta(days=days)
    kept = []
    removed = 0

    if os.path.isfile(DETECTED_FACES_LOG_PATH):
        with open(DETECTED_FACES_LOG_PATH, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            for row in reader:
                if not row:
                    continue

                visit_time = _parse_visit_time(row.get("time"))
                if visit_time is not None and visit_time < cutoff:
                    removed += 1
                    continue

                kept.append(
                    [
                        (row.get("time") or "").strip(),
                        (row.get("Name") or row.get("name") or "").strip(),
                        (row.get("size") or "").strip(),
                    ]
                )

    _empty_detected_faces_log()
    with open(DETECTED_FACES_LOG_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(kept)

    return removed


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


@app.before_request
def require_login():
    if request.endpoint in ("login", "static"):
        return None

    if session.get("admin_authenticated"):
        return None

    return redirect(url_for("login", next=request.full_path))


def _set_detection_and_redirect(enabled, message):
    try:
        save_detection_enabled(enabled)
    except Exception as exc:
        return _redirect_with(f"Detectiestatus opslaan mislukt: {exc}", "error")
    return _redirect_with(message, "ok")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if verify_admin_password(request.form.get("password")):
            session["admin_authenticated"] = True
            next_url = request.form.get("next") or url_for("control_page")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("control_page")
            return redirect(next_url)

        return render_template(
            "login.html",
            title="Admin Login",
            msg="Invalid password.",
            next=request.form.get("next", ""),
        )

    return render_template(
        "login.html",
        title="Admin Login",
        msg=request.args.get("msg", ""),
        next=request.args.get("next", ""),
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login", msg="Logged out."))


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

@app.route("/smartvision")
def smartvision_page():
    return render_template(
        "smartvision.html",
        title="Smart Vision",
        active_page="smartvision",
        detection_enabled=detection_enabled(),
    )




@app.route("/camera/feed")
def camera_feed():
    return app.response_class(
        generate_camera_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/smartvision/feed")
def smartvision_feed():
    return app.response_class(
        generate_camera_frames(smartvision=True),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/faces")
def faces_page():
    return render_template(
        "faces.html",
        people=list_known_people_with_photos(known_dir=os.path.join(APP_DIR, "known")),
        msg=request.args.get("msg", ""),
        level=request.args.get("level", "info"),
    )


@app.route("/logs")
def logs_page():
    return render_template(
        "logs.html",
        title="Visit Logs",
        visits=read_detected_faces_log(),
        msg=request.args.get("msg", ""),
        level=request.args.get("level", "info"),
    )


@app.route("/logs/clear", methods=["POST"])
def clear_logs():
    try:
        _empty_detected_faces_log()
    except Exception as exc:
        return redirect(url_for("logs_page", msg=f"Failed to clear logs: {exc}", level="error"))
    return redirect(url_for("logs_page", msg="Visit log cleared.", level="ok"))


@app.route("/logs/prune", methods=["POST"])
def prune_logs():
    try:
        removed = prune_detected_faces_log(days=31)
    except Exception as exc:
        return redirect(url_for("logs_page", msg=f"Failed to delete old records: {exc}", level="error"))
    return redirect(url_for("logs_page", msg=f"Deleted {removed} old record(s).", level="ok"))


@app.route("/known/<person>")
def known_person_page(person):
    person_dir = os.path.join(APP_DIR, "known", person)
    if not os.path.isdir(person_dir):
        return redirect(url_for("faces_page", msg=f"Persoon '{person}' niet gevonden.", level="error"))
    
    files = []
    if os.path.exists(person_dir):
        for fn in os.listdir(person_dir):
            if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                files.append(fn)
    files.sort()
    
    return render_template(
        "known_person.html",
        person=person,
        files=files,
        msg=request.args.get("msg", ""),
        level=request.args.get("level", "info"),
    )


@app.route("/known/<person>/<filename>")
def known_person_file(person, filename):
    person_dir = os.path.join(APP_DIR, "known", person)
    return send_from_directory(person_dir, filename)


@app.route("/known/<person>/photo/delete", methods=["POST"])
def known_photo_delete(person):
    filename = request.form.get("filename")
    if not filename:
        return redirect(url_for("known_person_page", person=person, msg="Geen foto opgegeven.", level="error"))

    safe_filename = os.path.basename(filename)
    person_dir = os.path.join(APP_DIR, "known", person)
    photo_path = os.path.join(person_dir, safe_filename)

    if not os.path.isfile(photo_path):
        return redirect(url_for("known_person_page", person=person, msg="Foto niet gevonden.", level="error"))

    try:
        os.remove(photo_path)
        return redirect(url_for("known_person_page", person=person, msg=f"Foto '{safe_filename}' verwijderd.", level="success"))
    except Exception as e:
        return redirect(url_for("known_person_page", person=person, msg=f"Fout bij verwijderen van foto: {e}", level="error"))


@app.route("/known/delete", methods=["POST"])
def known_delete():
    person = request.form.get("person")
    if not person:
        return redirect(url_for("faces_page", msg="Geen persoon opgegeven.", level="error"))
    
    person_dir = os.path.join(APP_DIR, "known", person)
    npz_file = os.path.join(APP_DIR, "known", f"{person}.npz")
    
    try:
        if os.path.exists(person_dir):
            shutil.rmtree(person_dir)
        if os.path.exists(npz_file):
            os.remove(npz_file)
        return redirect(url_for("faces_page", msg=f"Persoon '{person}' verwijderd.", level="success"))
    except Exception as e:
        return redirect(url_for("faces_page", msg=f"Fout bij verwijderen: {e}", level="error"))


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


@app.route("/detection-size", methods=["POST"])
def set_detection_size():
    try:
        size = save_detection_size(request.form.get("detection_size"))
    except Exception as exc:
        return _redirect_with(f"Detection size save failed: {exc}", "error")
    return _redirect_with(f"Detection size saved at {size}px.", "ok")


@app.route("/password", methods=["POST"])
def set_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not verify_admin_password(current_password):
        return _redirect_with("Current password is incorrect.", "error")

    if len(new_password) < 8:
        return _redirect_with("New password must be at least 8 characters.", "error")

    if new_password != confirm_password:
        return _redirect_with("New passwords do not match.", "error")

    save_admin_password(new_password)
    return _redirect_with("Admin password changed.", "ok")


@app.route("/reboot", methods=["POST"])
def reboot_system():
    _run_system_action_later(_system_action_commands("reboot"))
    return _redirect_with("Jetson reboot requested.", "ok")

@app.route("/shutdown", methods=["POST"])
def shutdown_system():
    _run_system_action_later(_system_action_commands("poweroff"))
    return _redirect_with("Jetson shutdown requested.", "ok")



ensure_admin_password_hash()
app.secret_key = os.environ.get("FACEASSIST_SECRET_KEY", ensure_admin_session_secret())


if __name__ == "__main__":
    app.run(host=CONFIG_HOST, port=CONFIG_PORT, debug=False)
