"""Bisect-style: copy meeting_0506 keeping only first N slides; test each."""
import sys, os, shutil, subprocess
from pptx import Presentation
import zipfile, re

SRC = r"DOC\會議紀錄\meeting_0506_洪大甲.pptx"
QA = r"tools\pptx\qa"


def make_subset(n):
    p = Presentation(SRC)
    # Drop slides after index n-1
    xml_slides = p.slides._sldIdLst
    slides = list(xml_slides)
    for s in slides[n:]:
        xml_slides.remove(s)
    out = os.path.join(QA, f"sub_{n}.pptx")
    p.save(out)
    return out


for n in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
    f = make_subset(n)
    print(f"Made {f} with {n} slides")
