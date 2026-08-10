# -*- coding: utf-8 -*-
"""Export the 20260810 TANET docx to PDF via Word COM, updating fields first."""
import os
import win32com.client as win32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = ("A_Comparative_Study_and_Embedded_Implementation_of_SOC_Estimation_Methods_"
        "for_Lithium-ion_Batteries_20260810")
docx = os.path.join(HERE, BASE + ".docx")
pdf = os.path.join(HERE, BASE + ".pdf")

word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = False
try:
    d = word.Documents.Open(docx, ReadOnly=False)
    try:
        d.Fields.Update()
        for s in d.StoryRanges:
            s.Fields.Update()
    except Exception as e:
        print("field update warn:", e)
    d.Repaginate()
    print("PAGES:", d.ComputeStatistics(2))     # wdStatisticPages
    d.SaveAs(pdf, FileFormat=17)                # wdFormatPDF
    d.Close(False)
finally:
    word.Quit()
print("saved", pdf)
