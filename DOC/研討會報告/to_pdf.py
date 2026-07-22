# -*- coding: utf-8 -*-
"""Export the TANET docx to PDF via Word COM, updating fields/TOC first."""
import os
import sys
import win32com.client as win32

HERE = os.path.dirname(os.path.abspath(__file__))
docx = os.path.join(HERE, "A_Comparative_Study_and_Embedded_Implementation_of_SOC_Estimation_Methods_for_Lithium-ion_Batteries.docx")
pdf = os.path.join(HERE, "A_Comparative_Study_and_Embedded_Implementation_of_SOC_Estimation_Methods_for_Lithium-ion_Batteries.pdf")

word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = False
try:
    d = word.Documents.Open(docx, ReadOnly=False)
    # update all fields (page refs etc.)
    try:
        d.Fields.Update()
        for s in d.StoryRanges:
            s.Fields.Update()
    except Exception as e:
        print("field update warn:", e)
    d.Repaginate()
    npages = d.ComputeStatistics(2)  # wdStatisticPages
    print("PAGES:", npages)
    d.SaveAs(pdf, FileFormat=17)     # wdFormatPDF
    d.Close(False)
finally:
    word.Quit()
print("saved", pdf)
