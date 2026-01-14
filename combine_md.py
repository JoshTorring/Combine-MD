#!/usr/bin/env python3
import os, re, shlex, shutil, hashlib, argparse

IMG_EXTS = {".png",".jpg",".jpeg",".gif",".webp",".svg",".bmp",".tif",".tiff"}

def natkey(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def is_url(p: str) -> bool:
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*:', p))

def short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:8]

def safe_out_name(src_full: str, outdir: str, used: dict) -> str:
    base = os.path.basename(src_full)
    dst = os.path.join(outdir, base)
    key = base.lower()
    if key not in used and not os.path.exists(dst):
        used[key] = src_full
        return base
    stem, ext = os.path.splitext(base)
    new = f"{stem}_{short_hash(src_full)}{ext}"
    used[new.lower()] = src_full
    return new

def md_escape_title(s: str) -> str:
    return re.sub(r"[\r\n\t]+", " ", s).strip()

def slug(s: str) -> str:
    # filesystem-friendly (keeps spaces; removes weird characters)
    s = re.sub(r"[\/\\:<>\"|\?\*]", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120] if len(s) > 120 else s

def main():
    ap = argparse.ArgumentParser(description="Flatten + rewrite Obsidian markdown and copy images for pandoc.")
    ap.add_argument("vault", help="Path to the Obsidian vault (root folder)")
    ap.add_argument("--outdir-name", default="combined_output_folder", help="Output folder name inside the vault")
    ap.add_argument("--tmpdir-name", default="_tmp_md_flat", help="Temp md folder name inside output folder")
    ap.add_argument("--ignore", action="append", default=[], help="Folder name to ignore (repeatable)")
    ap.add_argument("--folder-heading-level", type=int, default=1, help="Markdown heading level for folders (default: 1)")
    ap.add_argument("--file-heading-level", type=int, default=2, help="Markdown heading level for files (default: 2)")
    ap.add_argument("--show-vault-root-as", default="Vault root", help='Folder title to use for files in the vault root')
    args = ap.parse_args()

    ROOT = os.path.abspath(os.path.expanduser(args.vault))
    if not os.path.isdir(ROOT):
        raise SystemExit(f"Vault path not found or not a directory: {ROOT}")

    OUTDIR = os.path.join(ROOT, args.outdir_name)
    TMPDIR = os.path.join(OUTDIR, args.tmpdir_name)

    IGNORE_DIRS = {args.outdir_name.lower()}
    IGNORE_DIRS.update(x.strip().lower() for x in args.ignore if x.strip())

    os.makedirs(TMPDIR, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

    def should_skip_dir(dirpath: str) -> bool:
        rel = os.path.relpath(dirpath, ROOT)
        parts = [] if rel in (".", "") else rel.split(os.sep)
        return any(p.lower() in IGNORE_DIRS for p in parts)

    # Collect ALL images + basename index
    image_index = {}
    image_files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORE_DIRS]
        if should_skip_dir(dirpath):
            dirnames[:] = []
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in IMG_EXTS:
                full = os.path.join(dirpath, fn)
                image_files.append(full)
                image_index.setdefault(fn.lower(), []).append(full)

    # Find markdown files
    md_files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORE_DIRS]
        if should_skip_dir(dirpath):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.lower().endswith(".md"):
                md_files.append(os.path.join(dirpath, fn))

    # Sort by relative path so files from same folder stay grouped
    md_files.sort(key=lambda p: natkey(os.path.relpath(p, ROOT)))

    # --- Flat image copy into OUTDIR ---
    copied_img_map = {}
    used_img_names = {}

    def resolve_image(ref: str, md_dir: str):
        ref = ref.strip()
        if not ref or is_url(ref):
            return None
        ref = ref.replace("\\", "/")

        if os.path.isabs(ref) and os.path.exists(ref):
            return os.path.normpath(ref)

        candidate = os.path.normpath(os.path.join(md_dir, ref))
        if os.path.exists(candidate):
            return candidate

        base = os.path.basename(ref).lower()
        hits = image_index.get(base, [])
        return hits[0] if hits else None

    def copy_image_and_get_rel(src_full: str):
        src_full = os.path.normpath(src_full)
        if src_full in copied_img_map:
            return copied_img_map[src_full]

        dst_name = safe_out_name(src_full, OUTDIR, used_img_names)
        shutil.copy2(src_full, os.path.join(OUTDIR, dst_name))
        copied_img_map[src_full] = dst_name
        return dst_name

    # Regexes
    re_obsidian = re.compile(r'!\[\[([^\]\|]+?)(?:\|[^\]]*)?\]\]')
    re_md_img   = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    re_html_img = re.compile(r'(<img\b[^>]*\bsrc=)(["\'])([^"\']+)(\2)', re.IGNORECASE)

    last_folder_title = None
    folder_h = "#" * max(1, min(6, args.folder_heading_level))
    file_h   = "#" * max(1, min(6, args.file_heading_level))

    def folder_title_for(md_path: str) -> str:
        rel = os.path.relpath(os.path.dirname(md_path), ROOT)
        if rel in (".", ""):
            return args.show_vault_root_as
        return rel.replace(os.sep, " / ")

    def file_title_for(md_path: str) -> str:
        return os.path.splitext(os.path.basename(md_path))[0]

    # Write temp MDs with numeric prefixes so *_tmp_md_flat/*.md globs in correct order
    seq = 0

    for md_path in md_files:
        seq += 1
        md_dir = os.path.dirname(md_path)
        rel_md = os.path.relpath(md_path, ROOT)

        text = open(md_path, "r", encoding="utf-8", errors="ignore").read()

        def sub_obs(m):
            target = m.group(1).strip()
            if os.path.splitext(target)[1].lower() not in IMG_EXTS:
                return m.group(0)
            src = resolve_image(target, md_dir)
            if not src:
                return m.group(0)
            return f"![]({copy_image_and_get_rel(src)})"

        text2 = re_obsidian.sub(sub_obs, text)

        def sub_md(m):
            alt = m.group(1)
            inner = m.group(2).strip()
            inner2 = inner[1:-1] if inner.startswith("<") and inner.endswith(">") else inner
            try:
                parts = shlex.split(inner2)
            except ValueError:
                parts = [inner2]
            if not parts:
                return m.group(0)

            path = parts[0]
            if os.path.splitext(path)[1].lower() not in IMG_EXTS:
                return m.group(0)

            src = resolve_image(path, md_dir)
            if not src:
                return m.group(0)

            rest = (" " + " ".join(parts[1:])) if len(parts) > 1 else ""
            return f"![{alt}]({copy_image_and_get_rel(src)}{rest})"

        text2 = re_md_img.sub(sub_md, text2)

        def sub_html(m):
            prefix, q, srcp, _ = m.group(1), m.group(2), m.group(3), m.group(4)
            if os.path.splitext(srcp)[1].lower() not in IMG_EXTS:
                return m.group(0)
            src = resolve_image(srcp, md_dir)
            if not src:
                return m.group(0)
            return f"{prefix}{q}{copy_image_and_get_rel(src)}{q}"

        text2 = re_html_img.sub(sub_html, text2)

        folder_title = md_escape_title(folder_title_for(md_path))
        file_title = md_escape_title(file_title_for(md_path))

        heading_block = ""
        if folder_title != last_folder_title:
            heading_block += f"\n\n{folder_h} {folder_title}\n\n"
            last_folder_title = folder_title
        heading_block += f"{file_h} {file_title}\n\n"

        text2 = heading_block + text2 + f"\n\n<!-- Source: {rel_md} -->\n\n"

        out_name = f"{seq:06d}__{slug(folder_title)}__{slug(file_title)}.md"
        out_md = os.path.join(TMPDIR, out_name)
        with open(out_md, "w", encoding="utf-8", errors="ignore") as f:
            f.write(text2)

    # Copy ALL images (including unreferenced)
    for img in image_files:
        try:
            copy_image_and_get_rel(img)
        except Exception:
            pass

if __name__ == "__main__":
    main()
