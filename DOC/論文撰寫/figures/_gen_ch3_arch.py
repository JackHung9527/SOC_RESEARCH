# -*- coding: utf-8 -*-
"""產生圖 3-1 測試平台系統架構（正式方塊圖）。"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent
CJK = 'Microsoft JhengHei'
plt.rcParams['font.family'] = CJK
plt.rcParams['axes.unicode_minus'] = False
ARROW = '#5A5A5A'; TXT = '#1A1A1A'
S = {'host': dict(fc='#2E5C9A', ec='#1F3864', tc='white'),
     'inst': dict(fc='#DCE6F4', ec='#2E5C9A', tc=TXT),
     'mcu':  dict(fc='#E2EFDA', ec='#548235', tc=TXT),
     'dut':  dict(fc='#FFF2CC', ec='#BF9000', tc=TXT)}


def box(ax, cx, cy, w, h, lines, kind):
    st = S[kind]
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                 boxstyle='round,pad=0.02,rounding_size=0.10',
                 fc=st['fc'], ec=st['ec'], lw=1.9))
    n = len(lines)
    for i, (t, b, fs) in enumerate(lines):
        yy = cy + (n-1)/2*0.42 - i*0.42
        ax.text(cx, yy, t, ha='center', va='center', family=CJK,
                fontsize=fs, fontweight=('bold' if b else 'normal'), color=st['tc'])


def arrow(ax, p1, p2, label=None, lx=0.12):
    ax.annotate('', xy=p2, xytext=p1, arrowprops=dict(arrowstyle='-|>', color=ARROW,
                lw=1.8, shrinkA=2, shrinkB=2, mutation_scale=15))
    if label:
        mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
        ax.text(mx+lx, my, label, ha='left', va='center', family=CJK, fontsize=9.5, color='#666')


fig, ax = plt.subplots(figsize=(8.2, 6.2), dpi=200)
ax.set_xlim(0, 12); ax.set_ylim(0, 10); ax.axis('off')

box(ax, 6.0, 9.0, 7.2, 1.0, [('上位機（自動化排程 · 安全監控 · 資料紀錄）', True, 12.5)], 'host')
box(ax, 2.3, 6.2, 3.0, 1.5, [('IT6302 直流電源', True, 11.5), ('充電路徑（CC-CV）', False, 10)], 'inst')
box(ax, 6.0, 6.2, 3.0, 1.5, [('IT8512A+ 電子負載', True, 11.5), ('放電路徑（CC）', False, 10)], 'inst')
box(ax, 9.7, 6.2, 3.2, 1.5, [('STM32 + INA226', True, 11.5), ('嵌入式估測標的', False, 10)], 'mcu')
box(ax, 4.15, 2.8, 3.4, 1.4, [('DUT 受測電池', True, 12), ('NMC 2000 mAh', False, 10)], 'dut')

# host -> instruments
arrow(ax, (2.3, 8.5), (2.3, 6.95), 'SCPI／USB')
arrow(ax, (6.0, 8.5), (6.0, 6.95), 'SCPI／USB')
arrow(ax, (9.7, 8.5), (9.7, 6.95), 'USB（狀態回報）')
# instruments -> DUT (充放電)
arrow(ax, (2.6, 5.45), (3.6, 3.5), '充電')
arrow(ax, (5.7, 5.45), (4.7, 3.5), '放電')
# DUT -> MCU/INA226 量測
arrow(ax, (5.85, 2.8), (8.4, 5.45), '經 10 mΩ shunt 量測 V／I')

fig.tight_layout()
fig.savefig(OUT / 'fig3-1.png', dpi=200, bbox_inches='tight', pad_inches=0.08, facecolor='white')
plt.close(fig)
print('saved fig3-1.png')
