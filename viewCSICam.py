#!/usr/bin/env python3
import argparse
import subprocess
import sys


def build_command(sensor_id=0, width=1280, height=720, framerate=30):
    return [
        "gst-launch-1.0",
        "nvarguscamerasrc",
        f"sensor-id={sensor_id}",
        "!",
        f"video/x-raw(memory:NVMM),width={width},height={height},framerate={framerate}/1",
        "!",
        "nvvidconv",
        "!",
        "nveglglessink",
    ]


def main():
    parser = argparse.ArgumentParser(description="Show the Jetson CSI camera preview.")
    parser.add_argument("--sensor-id", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--framerate", type=int, default=30)
    args = parser.parse_args()

    command = build_command(
        sensor_id=args.sensor_id,
        width=args.width,
        height=args.height,
        framerate=args.framerate,
    )

    try:
        return subprocess.run(command, check=False).returncode
    except FileNotFoundError:
        print("gst-launch-1.0 not found. Install/check GStreamer on the Jetson.", file=sys.stderr)
        return 127


if __name__ == "__main__":
    raise SystemExit(main())
