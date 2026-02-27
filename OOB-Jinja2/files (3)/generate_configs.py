#!/usr/bin/env python3
"""
generate_configs.py
-------------------
Generates Juniper EX4100 / EX4400 set-format configuration files
from Jinja2 templates and a YAML device-data file.

Output: one file per device, named by serial number.
        e.g.  output/FW3523AB0001.conf

Usage:
    python generate_configs.py [--devices devices.yaml]
                               [--templates ./templates]
                               [--output ./output]
                               [--serial <SERIAL>]       # optional: single device
                               [--templates-list snmpv3 ntp syslog tacacs system_hardening]
"""

import argparse
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed. Run: pip install pyyaml")

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
except ImportError:
    sys.exit("Jinja2 not installed. Run: pip install jinja2")


# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_TEMPLATES_DIR = "./templates"
DEFAULT_DEVICES_FILE  = "./devices.yaml"
DEFAULT_OUTPUT_DIR    = "./output"

# Order matters — configs will be assembled in this sequence
DEFAULT_TEMPLATE_ORDER = [
    "system_hardening",
    "interfaces",
    "ntp",
    "syslog",
    "tacacs",
    "snmpv3",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_devices(devices_file: str) -> list[dict]:
    """Load and validate device data from YAML."""
    path = Path(devices_file)
    if not path.exists():
        log.error("Devices file not found: %s", devices_file)
        sys.exit(1)
    with open(path) as fh:
        data = yaml.safe_load(fh)
    devices = data.get("devices", [])
    if not devices:
        log.error("No devices found in %s", devices_file)
        sys.exit(1)
    # Validate required fields
    for dev in devices:
        if "serial" not in dev:
            log.error("Device entry missing 'serial': %s", dev)
            sys.exit(1)
        if "model" not in dev:
            log.warning("Device %s has no 'model' field — defaulting to EX4100", dev["serial"])
            dev["model"] = "EX4100"
    return devices


def build_jinja_env(templates_dir: str) -> Environment:
    """Create a Jinja2 environment with strict undefined checking."""
    tdir = Path(templates_dir)
    if not tdir.is_dir():
        log.error("Templates directory not found: %s", templates_dir)
        sys.exit(1)
    env = Environment(
        loader=FileSystemLoader(str(tdir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env


def render_template(env: Environment, template_name: str, context: dict) -> str | None:
    """Render a single template. Returns None if template not found."""
    filename = f"{template_name}.j2"
    try:
        tmpl = env.get_template(filename)
    except TemplateNotFound:
        log.warning("Template not found, skipping: %s", filename)
        return None
    try:
        return tmpl.render(**context)
    except Exception as exc:  # jinja2.UndefinedError etc.
        log.error("Error rendering %s for device %s: %s",
                  filename, context.get("serial", "?"), exc)
        return None


def generate_device_config(
    device: dict,
    env: Environment,
    template_names: list[str],
) -> str:
    """Combine all template renders for a single device into one config string."""
    serial  = device["serial"]
    model   = device["model"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = (
        f"# ============================================================\n"
        f"# Device  : {serial}\n"
        f"# Model   : {model}\n"
        f"# Host    : {device.get('hostname', 'N/A')}\n"
        f"# Generated: {now_str}\n"
        f"# ============================================================\n\n"
    )

    sections = [header]
    for tmpl_name in template_names:
        rendered = render_template(env, tmpl_name, device)
        if rendered:
            sections.append(
                f"# ---- {tmpl_name.upper().replace('_', ' ')} "
                f"{'─' * max(0, 50 - len(tmpl_name))} #\n"
            )
            sections.append(rendered.strip() + "\n\n")

    return "".join(sections)


def write_config(output_dir: str, serial: str, config: str) -> Path:
    """Write config to <output_dir>/<serial>.conf"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    out_file = out / f"{serial}.conf"
    out_file.write_text(config, encoding="utf-8")
    return out_file


# ── Main ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Juniper EX set-format configs from Jinja2 templates.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--devices", default=DEFAULT_DEVICES_FILE,
        help=f"Path to YAML device data file (default: {DEFAULT_DEVICES_FILE})",
    )
    parser.add_argument(
        "--templates", default=DEFAULT_TEMPLATES_DIR,
        help=f"Path to Jinja2 templates directory (default: {DEFAULT_TEMPLATES_DIR})",
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for generated configs (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--serial", default=None,
        help="Only generate config for this specific serial number",
    )
    parser.add_argument(
        "--templates-list", nargs="+", default=DEFAULT_TEMPLATE_ORDER,
        metavar="TEMPLATE",
        help=(
            "Ordered list of template base names to render\n"
            f"(default: {' '.join(DEFAULT_TEMPLATE_ORDER)})"
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print generated configs to stdout instead of writing files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log.info("Loading devices from: %s", args.devices)
    devices = load_devices(args.devices)

    if args.serial:
        devices = [d for d in devices if d["serial"] == args.serial]
        if not devices:
            log.error("Serial %s not found in devices file.", args.serial)
            sys.exit(1)

    log.info("Building Jinja2 environment from: %s", args.templates)
    env = build_jinja_env(args.templates)

    log.info("Templates to render (in order): %s", ", ".join(args.templates_list))

    results = {"ok": [], "failed": []}

    for device in devices:
        serial = device["serial"]
        log.info("Generating config for %s (%s)…", serial, device.get("model", "?"))

        config = generate_device_config(device, env, args.templates_list)

        if args.dry_run:
            print(f"\n{'═'*60}")
            print(config)
        else:
            out_file = write_config(args.output, serial, config)
            log.info("  ✔ Written: %s", out_file)
            results["ok"].append(serial)

    if not args.dry_run:
        log.info(
            "Done. %d succeeded, %d failed.",
            len(results["ok"]),
            len(results["failed"]),
        )
        if results["failed"]:
            log.warning("Failed serials: %s", ", ".join(results["failed"]))
            sys.exit(1)


if __name__ == "__main__":
    main()
