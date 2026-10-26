#!/usr/bin/env python3
"""glpi-label: print GLPI asset labels (name + QR code) on Zebra label printers.

  glpi-label print NAME URL [--copies N] [--preview out.png]
  glpi-label serve                 # local service used by the GLPI "Print label" button
  glpi-label calibrate             # let the printer measure label length and gap
  glpi-label ruler                 # print a mm grid to find label size and position
  glpi-label init                  # write a starter config file

Settings come from a JSON config file (see `glpi-label init`).
"""
import argparse
import json
import os
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

__version__ = "2.0.0"

DEFAULTS = {
    # GLPI address(es) allowed to use the service, e.g. "https://glpi.example.com"
    "glpi_url": [],
    "listen": {"host": "127.0.0.1", "port": 9123},
    "printer": {
        # cups: local CUPS queue (Linux/macOS), tcp: network printer (port 9100),
        # windows: Windows printer name (needs pywin32), file: write to a file/device
        "backend": "cups",
        "name": "",
        "host": "",
        "port": 9100,
        "path": "",
    },
    # epl: TLP/LP 2844 and older; zpl: most current Zebra printers
    "language": "epl",
    "dpi": 203,
    "head_width_mm": 104,
    # printable area; label length itself comes from printer calibration
    "label": {"width_mm": 40, "height_mm": 20},
    "font": "",
}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono-Bold.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "C:\\Windows\\Fonts\\consolab.ttf",
    "C:\\Windows\\Fonts\\courbd.ttf",
]


def config_path():
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "glpi-label" / "config.json"


def load_config(path):
    cfg = json.loads(json.dumps(DEFAULTS))
    if path.exists():
        user = json.loads(path.read_text(encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    if isinstance(cfg["glpi_url"], str):
        cfg["glpi_url"] = [cfg["glpi_url"]]
    cfg["glpi_url"] = [u.rstrip("/") for u in cfg["glpi_url"] if u]
    return cfg


# ---------------------------------------------------------------- rendering

def load_font(cfg, size):
    for path in [cfg.get("font")] + FONT_CANDIDATES:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def qr_matrix(text):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(text)
    qr.make(fit=True)
    return qr.get_matrix()


def draw_qr(d, matrix, x0, y0, mod):
    for y, row in enumerate(matrix):
        for x, v in enumerate(row):
            if v:
                d.rectangle([x0 + x * mod, y0 + y * mod,
                             x0 + (x + 1) * mod - 1, y0 + (y + 1) * mod - 1], fill=0)


def fit_font(cfg, d, text, max_w, max_h):
    size = max_h
    while size > 8:
        font = load_font(cfg, size)
        l, t, r, b = d.textbbox((0, 0), text, font=font)
        if r - l <= max_w and b - t <= max_h:
            break
        size -= 1
    return font, (l, t, r, b)


def render(cfg, name, url):
    """Name on top and QR code below, or side by side on long thin labels."""
    dpmm = cfg["dpi"] / 25.4
    W = round(cfg["label"]["width_mm"] * dpmm)
    H = round(cfg["label"]["height_mm"] * dpmm)
    img = Image.new("1", (W, H), 1)
    d = ImageDraw.Draw(img)
    margin = round(dpmm)
    matrix = qr_matrix(url)
    n = len(matrix) + 2  # 1-module quiet zone each side

    if W >= 3 * H:
        mod = max(1, (H - 2 * margin) // n)
        draw_qr(d, matrix, margin + mod, (H - n * mod) // 2 + mod, mod)
        left = margin + n * mod + margin
        font, (l, t, r, b) = fit_font(cfg, d, name, W - left - margin, H - 2 * margin)
        d.text((left + (W - left - margin - (r - l)) // 2 - l, (H - (b - t)) // 2 - t),
               name, font=font, fill=0)
        return img

    # keep text clear of rounded label corners
    font, (l, t, r, b) = fit_font(cfg, d, name, W - 4 * margin, H // 4)
    d.text(((W - (r - l)) // 2 - l, margin - t), name, font=font, fill=0)
    top = margin + (b - t)
    mod = max(1, (H - top - margin) // n)
    draw_qr(d, matrix, (W - n * mod) // 2 + mod, top + mod, mod)
    return img


def ruler_image(cfg):
    dpmm = cfg["dpi"] / 25.4
    W = round(cfg["head_width_mm"] * dpmm) // 8 * 8
    H = round(40 * dpmm)
    img = Image.new("1", (W, H), 1)
    d = ImageDraw.Draw(img)
    font = load_font(cfg, 14)
    tick = lambda mm: 24 if mm % 10 == 0 else 14 if mm % 5 == 0 else 6
    for mm in range(int(W / dpmm) + 1):
        x = round(mm * dpmm)
        d.line([x, 0, x, tick(mm)], fill=0)
        if mm % 10 == 0:
            d.text((x + 2, 26), str(mm), font=font, fill=0)
    for mm in range(1, 41):
        y = round(mm * dpmm)
        for x0 in range(0, W, round(20 * dpmm)):
            d.line([x0, y, x0 + tick(mm), y], fill=0)
            if mm % 10 == 0:
                d.text((x0 + 26, y - 8), str(mm), font=font, fill=0)
    return img


# ----------------------------------------------------------- printer languages

def encode(cfg, img, copies=1):
    W, H = img.size
    row_bytes = (W + 7) // 8
    padded = Image.new("1", (row_bytes * 8, H), 1)
    padded.paste(img, (0, 0))
    bits = padded.tobytes()  # PIL mode "1": bit 1 = white
    if cfg["language"] == "zpl":
        # ZPL ^GF: bit 1 = black
        data = bytes(b ^ 0xFF for b in bits).hex().upper()
        total = row_bytes * H
        return (f"^XA^PW{W}^LH0,0^FO0,0^GFA,{total},{total},{row_bytes},{data}^FS"
                f"^PQ{copies}^XZ").encode()
    # EPL GW: bit 0 = black, same polarity as PIL
    head = f"\nN\nR0,0\nZT\nq{W}\nGW0,0,{row_bytes},{H},".encode()
    return head + bits + f"\nP{copies}\n".encode()


def calibrate_cmd(cfg):
    return b"~JC" if cfg["language"] == "zpl" else b"\nxa\n"


# ------------------------------------------------------------------ backends

def send(cfg, data):
    p = cfg["printer"]
    backend = p["backend"]
    if backend == "cups":
        cmd = ["lp", "-o", "raw"] + (["-d", p["name"]] if p["name"] else [])
        subprocess.run(cmd, input=data, check=True, stdout=subprocess.DEVNULL)
    elif backend == "tcp":
        with socket.create_connection((p["host"], int(p["port"])), timeout=10) as s:
            s.sendall(data)
    elif backend == "windows":
        import win32print  # pip install pywin32
        h = win32print.OpenPrinter(p["name"] or win32print.GetDefaultPrinter())
        try:
            win32print.StartDocPrinter(h, 1, ("GLPI label", None, "RAW"))
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, data)
            win32print.EndPagePrinter(h)
            win32print.EndDocPrinter(h)
        finally:
            win32print.ClosePrinter(h)
    elif backend == "file":
        with open(p["path"], "ab") as f:
            f.write(data)
    else:
        raise ValueError(f"unknown printer backend: {backend}")


def print_label(cfg, name, url, copies=1):
    send(cfg, encode(cfg, render(cfg, name, url), copies))


# ------------------------------------------------------------------- service

def make_handler(cfg):
    origins = set(cfg["glpi_url"])

    class Handler(BaseHTTPRequestHandler):
        def _cors(self):
            origin = self.headers.get("Origin")
            if origin in origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.send_header("Vary", "Origin")

        def _reply(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self):
            self._reply(200, {"ok": True, "service": "glpi-label", "version": __version__})

        def do_POST(self):
            if self.path != "/print":
                return self._reply(404, {"error": "not found"})
            origin = self.headers.get("Origin")
            if origin is not None and origin not in origins:
                return self._reply(403, {"error": f"origin {origin} not allowed, add it to glpi_url"})
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                name = str(data["name"]).strip()
                url = str(data["url"]).strip()
                copies = max(1, min(int(data.get("copies", 1)), 20))
            except (ValueError, KeyError, TypeError):
                return self._reply(400, {"error": "bad request"})
            if not name or len(name) > 64 or not any(url.startswith(o + "/") for o in origins):
                return self._reply(400, {"error": "invalid name or url"})
            try:
                print_label(cfg, name, url, copies)
            except Exception as e:  # report printer errors to the GLPI page
                return self._reply(500, {"error": str(e)[-300:]})
            self._reply(200, {"ok": True, "printed": name, "url": url})

        def log_message(self, fmt, *args):
            print(fmt % args, flush=True)

    return Handler


def serve(cfg):
    if not cfg["glpi_url"]:
        sys.exit("set glpi_url in the config file first (glpi-label init)")
    host, port = cfg["listen"]["host"], int(cfg["listen"]["port"])
    print(f"glpi-label {__version__} listening on http://{host}:{port} "
          f"for {', '.join(cfg['glpi_url'])}", flush=True)
    ThreadingHTTPServer((host, port), make_handler(cfg)).serve_forever()


# ----------------------------------------------------------------------- cli

def main():
    p = argparse.ArgumentParser(prog="glpi-label", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", type=Path, default=config_path(),
                   help=f"config file (default: {config_path()})")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("print", help="print one label")
    pp.add_argument("name", help="text printed on the label")
    pp.add_argument("url", help="URL encoded in the QR code")
    pp.add_argument("--copies", type=int, default=1)
    pp.add_argument("--preview", metavar="PNG", help="write an image instead of printing")

    sub.add_parser("serve", help="run the local service for the GLPI button")
    sub.add_parser("calibrate", help="make the printer measure label length and gap")
    rp = sub.add_parser("ruler", help="print a mm grid to measure label size and position")
    rp.add_argument("--preview", metavar="PNG")
    ip = sub.add_parser("init", help="write a starter config file")
    ip.add_argument("--glpi-url", default="https://glpi.example.com")
    ip.add_argument("--force", action="store_true")

    a = p.parse_args()

    if a.cmd == "init":
        if a.config.exists() and not a.force:
            sys.exit(f"{a.config} already exists (use --force to overwrite)")
        cfg = json.loads(json.dumps(DEFAULTS))
        cfg["glpi_url"] = [a.glpi_url.rstrip("/")]
        a.config.parent.mkdir(parents=True, exist_ok=True)
        a.config.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {a.config}")
        return

    cfg = load_config(a.config)
    if a.cmd == "print":
        img = render(cfg, a.name, a.url)
        if a.preview:
            img.save(a.preview)
            print(f"preview -> {a.preview}")
        else:
            send(cfg, encode(cfg, img, a.copies))
            print(f"printed {a.name} -> {a.url}")
    elif a.cmd == "serve":
        serve(cfg)
    elif a.cmd == "calibrate":
        send(cfg, calibrate_cmd(cfg))
        print("calibration sent")
    elif a.cmd == "ruler":
        img = ruler_image(cfg)
        if a.preview:
            img.save(a.preview)
            print(f"preview -> {a.preview}")
        else:
            # full head width, no label length: shows where the label edges fall
            send(cfg, encode(cfg, img))
            print("ruler sent")


if __name__ == "__main__":
    main()
