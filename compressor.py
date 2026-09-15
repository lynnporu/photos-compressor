import os
import re
import shutil

import multiprocessing.pool

import tqdm

from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


CAM_ADDRESS = "/media/ptym/0123-4567/DCIM/130MSDCF"
DST_ADDRESS = os.getcwd()
THREADS = 16


def to_uncompressed_filename(name: str) -> str:
    return re.sub(r"(.*)-\d+.compressed.JPG", rf"\1.JPG", name)


def get_oldest_file(address: str = DST_ADDRESS):
    files = [
        file
        for file
        in os.listdir(address)
        if re.match(r".*\.JPG$", file)
    ]
    if not files:
        return None
    else:
        return list(sorted(files))[-1]


def get_files_to_copy(address: str = CAM_ADDRESS) -> list[str]:
    oldest_file = get_oldest_file(DST_ADDRESS) or "DSC00000-0.compressed.JPG"
    print(f"oldest file on `{DST_ADDRESS}` is `{oldest_file}`")
    uncompressed_oldest_name = to_uncompressed_filename(oldest_file)
    print(f"lookinf for files bigger than `{uncompressed_oldest_name}` from `{CAM_ADDRESS}`")

    files = [
        file
        for file
        in os.listdir(address)
        if re.match(r"DSC\d{5}\.JPG$", file) and (file > uncompressed_oldest_name)
    ]
    print(f"found {len(files)} files")
    return files


def get_files_to_compress(address: str = DST_ADDRESS) -> list[str]:
    files = [
        file
        for file
        in os.listdir(address)
        if re.match(r"DSC\d{5}\.JPG$", file)
    ]
    print(f"found {len(files)} files")
    return files


def resize(im: Image):
    new_width, new_height = int(im.width / 3), int(im.height / 3)
    return im.resize((new_width, new_height), Image.Resampling.LANCZOS)


def compress(addr: str):
    im = Image.open(addr)
    im = resize(im)

    i = 1
    while True:
        new_name = re.sub(r"(.*)\.JPG", rf"\1-{i}.compressed.JPG", addr)
        if os.path.isfile(new_name):
            i += 1
        else:
            break

    im.save(new_name, quality=80, exif=im.getexif())

    old_stat = os.stat(addr)
    new_stat = os.stat(new_name)
    compression = round(new_stat.st_size / old_stat.st_size * 100, 3)

    return addr, new_name, compression


def copy_to_dst(file, pbar):
    old = os.path.join(CAM_ADDRESS, file)
    new = os.path.join(DST_ADDRESS, file)
    shutil.copy(old, new)
    pbar.write(f"copy `{old}` -> `{new}`")


def split_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main():
    print(f"copying from `{CAM_ADDRESS}` to `{DST_ADDRESS}`")
    with tqdm.tqdm(sorted(get_files_to_copy())) as pbar:
        for file in pbar:
            copy_to_dst(file, pbar)

    print("compressing files")
    files_to_compress = sorted(get_files_to_compress())

    print(f"perform in {THREADS} threads")
    with multiprocessing.pool.Pool(THREADS) as p, tqdm.tqdm(total=len(files_to_compress)) as pbar:
        for addr, new_name, compression in p.imap(compress, files_to_compress):
            pbar.write(f"saved `{addr}` -> `{new_name}`, new size is {compression}% of old")
            pbar.update()
            pbar.refresh()
            os.remove(addr)


if __name__ == '__main__':
    main()
