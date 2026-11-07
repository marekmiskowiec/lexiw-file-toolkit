"""lexiw-file-toolkit: a small command-line kit for working with files.

Commands:
  convert   change image format (HEIC/JPEG/PNG/WebP...), optionally resize
  compress  shrink photos for uploading (Facebook etc.): resize + recompress
  rename    rename files in a folder using a pattern with a counter

Run `python toolkit.py <command> --help` for details.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

IMAGE_EXTENSIONS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
FORMATS = {"webp": "WEBP", "jpeg": "JPEG", "jpg": "JPEG", "png": "PNG"}
DEFAULT_FORMAT = "webp"


def find_images(folder: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in folder.glob(pattern) if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def resize(img: Image.Image, scale: float | None, max_size: int | None) -> Image.Image:
    width, height = img.size
    if scale and scale != 1:
        width, height = max(1, round(width * scale)), max(1, round(height * scale))
    if max_size and max(width, height) > max_size:
        ratio = max_size / max(width, height)
        width, height = max(1, round(width * ratio)), max(1, round(height * ratio))
    if (width, height) == img.size:
        return img
    return img.resize((width, height), Image.Resampling.LANCZOS)


def save_image(img: Image.Image, path: Path, fmt: str, quality: int) -> None:
    pil_format = FORMATS[fmt]
    if pil_format == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    options: dict = {}
    if pil_format == "WEBP":
        options = {"quality": quality, "method": 6}
    elif pil_format == "JPEG":
        options = {"quality": quality, "optimize": True, "progressive": True}
    elif pil_format == "PNG":
        options = {"optimize": True}
    # No exif= is passed on purpose: EXIF (incl. GPS location) is not copied to the output.
    img.save(path, pil_format, **options)


def process_images(args: argparse.Namespace) -> int:
    src = Path(args.input)
    out = Path(args.output)
    files = [src] if src.is_file() else find_images(src, args.recursive)
    if not files:
        print(f"No images found in {src}")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    ext = "jpg" if args.format in ("jpeg", "jpg") else args.format

    total_in = total_out = 0
    for path in files:
        rel = path.relative_to(src) if src.is_dir() else Path(path.name)
        target = (out / rel).with_suffix(f".{ext}")
        if target.exists() and not args.overwrite:
            print(f"skip   {rel} (exists, use --overwrite)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(path) as img:
                img = ImageOps.exif_transpose(img)  # keep correct rotation
                img = resize(img, args.scale, args.max_size)
                save_image(img, target, args.format, args.quality)
        except Exception as exc:  # keep going with the remaining files
            print(f"error  {rel}: {exc}", file=sys.stderr)
            continue
        size_in, size_out = path.stat().st_size, target.stat().st_size
        total_in += size_in
        total_out += size_out
        print(f"ok     {rel} -> {target.name}  {size_in / 1e6:.2f} MB -> {size_out / 1e6:.2f} MB")

    if total_in:
        print(f"\nDone: {total_in / 1e6:.1f} MB -> {total_out / 1e6:.1f} MB "
              f"({100 * total_out / total_in:.0f}% of original)")
    return 0


def rename_files(args: argparse.Namespace) -> int:
    folder = Path(args.folder)
    files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith("."))
    if args.ext:
        wanted = {e.lower().lstrip(".") for e in args.ext}
        files = [p for p in files if p.suffix.lower().lstrip(".") in wanted]
    if not files:
        print(f"No files to rename in {folder}")
        return 1

    plan = []
    for i, path in enumerate(files, start=args.start):
        new_stem = args.pattern.format(n=i, name=path.stem)
        new_path = path.with_name(new_stem + path.suffix.lower())
        if new_path != path:
            plan.append((path, new_path))

    targets = [new for _, new in plan]
    sources = {old for old, _ in plan}
    clashes = [t for t in targets if targets.count(t) > 1 or (t.exists() and t not in sources)]
    if clashes:
        print("Refusing to rename, these names would clash:", *sorted({c.name for c in clashes}), sep="\n  ")
        return 1

    for old, new in plan:
        print(f"{old.name} -> {new.name}")
    if not args.apply:
        print("\nDry run. Add --apply to really rename.")
        return 0

    # two-step rename so swapping names inside the same folder is safe
    temps = []
    for old, new in plan:
        tmp = old.with_name(f".tmp-rename-{old.name}")
        old.rename(tmp)
        temps.append((tmp, new))
    for tmp, new in temps:
        tmp.rename(new)
    print(f"\nRenamed {len(plan)} file(s).")
    return 0


def add_image_args(p: argparse.ArgumentParser, *, quality: int, scale: float | None) -> None:
    p.add_argument("input", nargs="?", default="input", help="file or folder (default: input)")
    p.add_argument("-o", "--output", default="output", help="output folder (default: output)")
    p.add_argument("-f", "--format", choices=sorted(FORMATS), default=DEFAULT_FORMAT,
                   help=f"output format (default: {DEFAULT_FORMAT})")
    p.add_argument("-q", "--quality", type=int, default=quality, help=f"1-100 (default: {quality})")
    p.add_argument("--scale", type=float, default=scale, help="resize factor, e.g. 0.5 = half size")
    p.add_argument("--max-size", type=int, help="limit the longer side to this many pixels")
    p.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    p.add_argument("--overwrite", action="store_true", help="overwrite existing output files")
    p.set_defaults(func=process_images)


def main() -> int:
    parser = argparse.ArgumentParser(description="lexiw-file-toolkit: convert, compress and rename files.")
    sub = parser.add_subparsers(dest="command", required=True)

    add_image_args(sub.add_parser("convert", help="change image format"), quality=90, scale=None)
    compress = sub.add_parser("compress", help="make photos lighter for uploading")
    add_image_args(compress, quality=80, scale=None)
    compress.set_defaults(max_size=2048)

    rn = sub.add_parser("rename", help="rename files using a pattern")
    rn.add_argument("folder", help="folder with files")
    rn.add_argument("-p", "--pattern", default="{n:03d}",
                    help="new name without extension; {n} = counter, {name} = old name "
                         "(default: {n:03d}, e.g. hot-wheels-{n:03d})")
    rn.add_argument("--start", type=int, default=1, help="first counter value (default: 1)")
    rn.add_argument("--ext", nargs="+", help="only these extensions, e.g. --ext jpg webp")
    rn.add_argument("--apply", action="store_true", help="really rename (default is a dry run)")
    rn.set_defaults(func=rename_files)

    args = parser.parse_args()
    if hasattr(args, "quality") and not 1 <= args.quality <= 100:
        parser.error("--quality must be between 1 and 100")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
