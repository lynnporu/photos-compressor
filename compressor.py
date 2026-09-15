# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11", "tqdm>=4.66"]
# ///

import argparse
import multiprocessing
import os
import shutil
import string
import sys
from functools import partial
from pathlib import Path

import tqdm
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

JPEG_SUFFIXES = {".jpg", ".jpeg"}
JUNK_PREFIX = "._"
CAMERA_DIR = "DCIM"
STAGING_DIR = ".staging"
DEFAULT_SCALE = 3
DEFAULT_QUALITY = 80
MAX_JOBS = 8
PHOTOS_PER_BATCH = 200
MOUNT_GLOBS = ("media/*/*", "run/media/*/*", "mnt/*", "Volumes/*")


def find_photos(folder: Path) -> list[Path]:
    return sorted(
        path for path in folder.rglob("*")
        if path.suffix.lower() in JPEG_SUFFIXES and not path.name.startswith(JUNK_PREFIX)
    )


def find_cards() -> list[Path]:
    if os.name == "nt":
        roots = [Path(f"{letter}:/") for letter in string.ascii_uppercase[2:]]
    else:
        roots = [path for glob in MOUNT_GLOBS for path in Path("/").glob(glob)]
    return [root / CAMERA_DIR for root in roots if (root / CAMERA_DIR).is_dir()]


def ask_for_source() -> Path | None:
    print(f"No --source given, looking for a {CAMERA_DIR} folder on removable drives...\n")
    cards = find_cards()
    if not cards:
        print(r"Found none. Re-run like:  uv run compressor.py --source E:\DCIM")
        return None
    for number, path in enumerate(cards, start=1):
        print(f"  [{number}] {path}  ({len(find_photos(path))} photos)")
    print("  [q] quit, I will pass --source myself\n")
    answer = input("pick one: ").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(cards):
        return cards[int(answer) - 1]
    return None


def copy_from_card(card_path: Path, staged_path: Path) -> None:
    staged_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = staged_path.with_suffix(staged_path.suffix + ".part")
    shutil.copy2(card_path, partial_path)
    os.replace(partial_path, staged_path)


def compress(task: tuple[str, str], scale: int, quality: int) -> tuple[str, str | None]:
    staged_path, out_path = Path(task[0]), Path(task[1])
    try:
        with Image.open(staged_path) as image:
            keep = {key: image.info[key] for key in ("exif", "icc_profile") if image.info.get(key)}
            smaller = image.resize(
                (max(1, image.width // scale), max(1, image.height // scale)),
                Image.Resampling.LANCZOS,
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        smaller.save(out_path, quality=quality, **keep)
        os.utime(out_path, (staged_path.stat().st_mtime,) * 2)
        return task[1], None
    except Exception as error:
        out_path.unlink(missing_ok=True)
        return task[1], f"{type(error).__name__}: {error}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compress the photos on your SD card.")
    parser.add_argument("--source", help=f"{CAMERA_DIR} folder on the card")
    parser.add_argument("--dest", default="compressed", help="where compressed photos go")
    parser.add_argument("--scale", type=int, default=DEFAULT_SCALE, help="shrink each side by this much")
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY, help="JPEG quality, 1..100")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 4, MAX_JOBS),
                        help="photos compressed at once")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source) if args.source else ask_for_source()
    if source is None:
        return 1
    if not source.is_dir():
        print(f"not a folder: {source}")
        return 1

    dest = Path(args.dest).resolve()
    staging = dest / STAGING_DIR
    tasks = [
        (photo, staging / photo.relative_to(source), dest / photo.relative_to(source))
        for photo in find_photos(source)
        if not (dest / photo.relative_to(source)).exists()
    ]
    print(f"{len(tasks)} new photos, {source} -> {dest}")
    if not tasks:
        return 0

    failed = []
    worker = partial(compress, scale=args.scale, quality=args.quality)
    pool = multiprocessing.get_context("spawn").Pool(args.jobs)
    with pool, tqdm.tqdm(total=len(tasks), unit="photo") as progress:
        for start in range(0, len(tasks), PHOTOS_PER_BATCH):
            staged = []
            for card_path, staged_path, out_path in tasks[start:start + PHOTOS_PER_BATCH]:
                try:
                    copy_from_card(card_path, staged_path)
                    staged.append((str(staged_path), str(out_path)))
                except OSError as error:
                    failed.append((card_path, error))
                    progress.update()
            for name, error in pool.imap_unordered(worker, staged):
                if error:
                    failed.append((name, error))
                progress.update()
            for staged_path, _ in staged:
                Path(staged_path).unlink(missing_ok=True)

    shutil.rmtree(staging, ignore_errors=True)
    print(f"\ndone: {len(tasks) - len(failed)} of {len(tasks)} into {dest}")
    for name, error in failed:
        print(f"  failed: {name}  {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
