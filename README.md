this will compress the photos on your SD card.

originals on the card are never modified or deleted. compressed copies land in a `compressed/` folder next to you, mirroring the folder layout of the card.

### before you start

plug the **SD card into a card reader**, not the camera into a USB cable. over a cable most cameras show up as an MTP device, which has no drive letter and cannot be read as a folder. if you only have the cable, set the camera's USB mode to `Mass Storage` first.

### how to use

**windows** — open PowerShell and install uv:

```
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macos / linux** — open a terminal and install uv:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

then, from the folder where you want the photos to end up:

```
uv run compressor.py
```

that is all — uv downloads python and the libraries by itself. with no arguments the script scans your drives for a `DCIM` folder and asks you to pick one. if it guesses wrong, quit and point it at the card yourself:

```
uv run compressor.py --source E:\DCIM
```

### options

| option | default | what it does |
| --- | --- | --- |
| `--source` | ask | the `DCIM` folder on the card |
| `--dest` | `compressed` | where compressed photos go |
| `--scale` | `3` | shrink each side by this factor |
| `--quality` | `80` | JPEG quality, 1..100 |
| `--jobs` | one per CPU core, max 8 | how many photos are compressed at once |

### running it more than once

safe. already compressed photos are skipped, so you can shoot more, run it again, and only the new ones are processed. if it is interrupted, just run it again.
