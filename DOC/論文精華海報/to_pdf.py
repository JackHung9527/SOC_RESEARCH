# -*- coding: utf-8 -*-
"""以 Word COM 將海報 docx 匯出為 PDF，並回報頁數。"""
import os
import win32com.client as win32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "論文精華海報_A4"
docx = os.path.join(HERE, BASE + ".docx")
pdf = os.path.join(HERE, BASE + ".pdf")

word = win32.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = False
try:
    d = word.Documents.Open(docx, ReadOnly=False)
    d.Repaginate()
    print("PAGES:", d.ComputeStatistics(2))     # wdStatisticPages
    d.SaveAs(pdf, FileFormat=17)                # wdFormatPDF
    d.Close(False)
finally:
    word.Quit()
print("saved", pdf)
