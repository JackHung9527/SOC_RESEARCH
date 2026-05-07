"""Patch pptxgenjs output to fix Content_Types references to nonexistent slide masters.

PptxGenJS sometimes emits one Override entry per slide pointing to slideMasterN.xml
even though only slideMaster1.xml is generated. PowerPoint refuses to open such files.
This script trims the Content_Types.xml to only reference actually-present parts.
"""
import sys
import zipfile
import shutil
import re
import os
import tempfile


def fix(pptx_path):
    pptx_path = os.path.abspath(pptx_path)
    with zipfile.ZipFile(pptx_path, "r") as z:
        names = set(z.namelist())
        ct = z.read("[Content_Types].xml").decode("utf-8")

    # Find every <Override PartName="/X" ContentType="..." />; if /X is not in zip, drop it
    pattern = re.compile(r'<Override\s+PartName="(/[^"]+)"\s+ContentType="[^"]+"\s*/>')

    def keep(match):
        part = match.group(1)
        # PartName starts with '/', zip entries don't
        zip_name = part.lstrip("/")
        if zip_name in names:
            return match.group(0)
        else:
            print(f"  drop missing reference: {part}")
            return ""

    new_ct = pattern.sub(keep, ct)

    if new_ct == ct:
        print("No changes needed for", pptx_path)
        return

    # Write back: zipfile can't update individual entries cleanly, repack
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pptx")
    os.close(tmp_fd)
    try:
        with zipfile.ZipFile(pptx_path, "r") as zin, zipfile.ZipFile(
            tmp_path, "w", zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                if item.filename == "[Content_Types].xml":
                    zout.writestr(item, new_ct)
                else:
                    zout.writestr(item, zin.read(item.filename))
        shutil.move(tmp_path, pptx_path)
        print("Fixed:", pptx_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fix_pptx.py <file.pptx>")
        sys.exit(1)
    for p in sys.argv[1:]:
        fix(p)
