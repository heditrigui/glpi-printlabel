# Print label for GLPI

Print asset labels — the asset's name and a QR code linking to its GLPI page — on a Zebra label printer, straight from GLPI with one click.

![GLPI](https://img.shields.io/badge/GLPI-10%20%7C%2011%20%7C%2012-blue) ![license](https://img.shields.io/badge/license-GPLv3%2B-green)

Used in production on GLPI 12 with a Zebra TLP 2844 (EPL). GLPI 10/11 and ZPL printers are supported by design; reports welcome.

```
┌──────────────────────┐
│    ACME-MONITOR-219  │
│       ▄▄▄▄▄▄▄        │
│       █ QR  █        │   QR → https://glpi.example.com/front/monitor.form.php?id=69
│       ▀▀▀▀▀▀▀        │
└──────────────────────┘
```

It has two parts:

| Part | Runs on | Does |
| --- | --- | --- |
| **`printlabel` GLPI plugin** | the GLPI server | Adds a **Print label** button next to **Save** on asset forms (computers, monitors, printers, phones, network devices, peripherals…). Builds the label text from a pattern you configure. |
| **`glpi-label` agent** | each computer that has a label printer | Small local service the button talks to. Draws the label and sends it to the printer. Also a command-line tool. |

The browser on the user's computer sends the label to the agent on that same computer (`http://127.0.0.1:9123` by default), so labels print on the printer next to the user — no printer setup on the GLPI server.

## Supported printers

Any Zebra (or compatible) printer that speaks **EPL** (TLP/LP 2844 and older) or **ZPL** (most current Zebra desktop and industrial printers), connected:

- by USB through **CUPS** (Linux, macOS),
- by USB on **Windows** (any installed printer, sent as RAW),
- over the **network** (raw TCP port 9100),
- or to a device/file (e.g. `/dev/usb/lp0`).

## 1. Install the GLPI plugin

1. Download `printlabel-<version>.zip` from the [releases](https://github.com/heditrigui/glpi-printlabel/releases) (or run `./build.sh`).
2. Unzip it into GLPI's `marketplace/` (or `plugins/`) folder so you get `marketplace/printlabel/setup.php`, owned by the web server user.
3. In GLPI: **Setup → Plugins → Print label → Install**, then **Enable**.
   Or from the GLPI folder:
   ```bash
   sudo -u www-data php bin/console plugin:install printlabel -u glpi
   sudo -u www-data php bin/console plugin:activate printlabel
   ```
4. Optional: click the wrench icon on the plugin to set the label text patterns (see below).

## 2. Install the agent on each computer with a printer

Needs Python 3.9+.

```bash
pipx install "git+https://github.com/heditrigui/glpi-printlabel.git#subdirectory=agent"
# Windows with a USB printer: pipx install "glpi-label[windows] @ git+https://github.com/heditrigui/glpi-printlabel.git#subdirectory=agent"
```

Create the config file, giving your GLPI address (the one in the browser's address bar):

```bash
glpi-label init --glpi-url https://glpi.example.com
```

This writes `~/.config/glpi-label/config.json` (Windows: `%APPDATA%\glpi-label\config.json`). Edit it for your printer:

```json
{
  "glpi_url": ["https://glpi.example.com"],
  "listen": {"host": "127.0.0.1", "port": 9123},
  "printer": {"backend": "cups", "name": "Zebra", "host": "", "port": 9100, "path": ""},
  "language": "epl",
  "dpi": 203,
  "head_width_mm": 104,
  "label": {"width_mm": 40, "height_mm": 20},
  "font": ""
}
```

| Key | Meaning |
| --- | --- |
| `glpi_url` | GLPI address(es) allowed to use the agent. Requests from any other site are refused. |
| `printer.backend` | `cups` (queue `name`), `windows` (printer `name`, empty = default), `tcp` (`host`:`port`), `file` (`path`). |
| `language` | `epl` or `zpl`. |
| `dpi` | 203 or 300, per your printer. |
| `label` | Printable area in mm. Label length/gap is measured by the printer (`glpi-label calibrate`). |
| `font` | Optional path to a TTF font. Defaults to DejaVu Sans Mono Bold / Menlo / Consolas. |

### Printer setup

**Linux / macOS (USB):** create a raw CUPS queue for the printer:

```bash
lpinfo -v | grep -i zebra                          # find the device URI
lpadmin -p Zebra -E -v 'usb://Zebra/TLP2844?serial=XXXX' -m raw
```

**Windows (USB):** install the printer with its Zebra driver and put its name in `printer.name` with `"backend": "windows"`.

**Network printer:** `"backend": "tcp", "host": "192.0.2.50"`.

### Fit the labels

```bash
glpi-label calibrate     # printer feeds a few labels and learns their length and gap
glpi-label ruler         # prints a mm grid: read where the label edges fall
glpi-label print TEST https://glpi.example.com/ --preview test.png   # check layout without printing
glpi-label print TEST https://glpi.example.com/
```

Set `label.width_mm` to the label width and `label.height_mm` to a little less than its length. Long thin labels (width ≥ 3× height) get the QR code on the left and the text on the right.

### Run the agent at logon

- **Linux (systemd):** `cp agent/service/glpi-label.service ~/.config/systemd/user/ && systemctl --user enable --now glpi-label`
- **macOS:** see `agent/service/com.github.glpi-label.plist`.
- **Windows:** run `agent/service/install-windows-task.ps1` in PowerShell.

Check it: `curl http://127.0.0.1:9123/` → `{"ok": true, ...}`.

## Label text patterns

Configured in GLPI (**Setup → Plugins → Print label**, wrench icon), one `itemtype=pattern` per line; `default` applies to the other item types:

```
default={name}
computer=ACME-{type}-{otherserial}
monitor=ACME-MONITOR-{otherserial}
```

| Placeholder | Value |
| --- | --- |
| `{name}` | Item name |
| `{otherserial}` | Inventory number |
| `{serial}` | Serial number |
| `{id}` | GLPI ID |
| `{itemtype}` | Item type from the URL (`computer`, `monitor`…) |
| `{type}` | The item's type dropdown (e.g. `Laptop`) |

`{type|itemtype}` uses the first non-empty value; `{itemtype:upper}` / `:lower` changes case. If a placeholder is empty, the item name is printed instead. The text can always be edited in the prompt before printing.

## Troubleshooting

- **No button:** the plugin must be enabled; reload with Ctrl+F5. The button appears on forms that have an *Inventory number* field.
- **"Label not printed (is the glpi-label agent running…)":** start the agent; check `glpi_url` matches the GLPI address exactly (scheme and host). Chromium-based browsers may ask to allow access to *devices on your local network* — allow it for your GLPI site. Brave: lower Shields for the GLPI site if needed.
- **Prints across two labels / drifts:** `glpi-label calibrate`.
- **Part of the label is blank, ragged edge:** usually the ribbon (thermal-transfer printers) is not covering the label width.
- **Wrong size or position:** `glpi-label ruler`, then adjust `label` in the config.

## Security

The agent listens on `127.0.0.1` only, accepts print requests only from the GLPI addresses in `glpi_url`, and only prints URLs that point to those GLPI addresses.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
