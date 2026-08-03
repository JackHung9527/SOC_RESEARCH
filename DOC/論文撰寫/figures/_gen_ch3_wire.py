# -*- coding: utf-8 -*-
"""產生圖 3-2 量測迴路接線圖（迴路級）。

風格比照 _gen_ch3_arch.py（圖 3-1）：粗線為功率迴路、細線為量測／通訊訊號。
標籤一律以絕對座標放置，離線離框 >= 0.25 單位，不得與線或方塊重疊。
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib import font_manager

OUT = Path(__file__).resolve().parent
CJK = 'Microsoft JhengHei'
if not any(f.name == CJK for f in font_manager.fontManager.ttflist):
    CJK = 'Noto Sans CJK TC'
plt.rcParams['font.family'] = CJK
plt.rcParams['axes.unicode_minus'] = False

TXT = '#1A1A1A'
PWR = '#C00000'      # 功率迴路（充放電大電流）
RTN = '#404040'      # 迴流／共地
SIG = '#2E5C9A'      # 量測與通訊訊號
S = {'inst': dict(fc='#DCE6F4', ec='#2E5C9A', tc=TXT),
     'mcu':  dict(fc='#E2EFDA', ec='#548235', tc=TXT),
     'dut':  dict(fc='#FFF2CC', ec='#BF9000', tc=TXT),
     'host': dict(fc='#2E5C9A', ec='#1F3864', tc='white')}


def box(ax, cx, cy, w, h, lines, kind, lw=1.9):
    st = S[kind]
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                 boxstyle='round,pad=0.02,rounding_size=0.10',
                 fc=st['fc'], ec=st['ec'], lw=lw, zorder=3))
    n = len(lines)
    for i, (t, b, fs) in enumerate(lines):
        yy = cy + (n - 1) / 2 * 0.40 - i * 0.40
        ax.text(cx, yy, t, ha='center', va='center', family=CJK, zorder=4,
                fontsize=fs, fontweight=('bold' if b else 'normal'), color=st['tc'])


def wire(ax, pts, color=PWR, lw=3.0, ls='-', z=2):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=color, lw=lw, ls=ls, solid_capstyle='round', zorder=z)


def arrow(ax, p1, p2, color=SIG, lw=1.6, ls='-'):
    ax.annotate('', xy=p2, xytext=p1, zorder=3,
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=0, mutation_scale=13))


def node(ax, x, y, color=PWR):
    ax.plot([x], [y], marker='o', ms=5.5, color=color, zorder=5)


def lbl(ax, x, y, t, fs=9.5, color='#555', ha='center', weight='normal'):
    ax.text(x, y, t, ha=ha, va='center', family=CJK, fontsize=fs,
            color=color, fontweight=weight, zorder=6)


fig, ax = plt.subplots(figsize=(7.8, 5.96), dpi=200)
ax.set_xlim(0, 15.5); ax.set_ylim(-0.2, 11.4); ax.axis('off')

# ---------------- 功率迴路（上半部） ----------------
box(ax, 2.2, 8.2, 2.6, 1.9,
    [('DUT', True, 12.5), ('受測電池', False, 10.5), ('鋰離子 2000 mAh', False, 9.5)], 'dut')
lbl(ax, 3.75, 8.95, '+', fs=13, color=PWR, weight='bold')
lbl(ax, 3.75, 6.95, '-', fs=13, color=RTN, weight='bold')

A, B = 5.6, 7.4          # shunt 兩端 x
YP = 8.6                 # 功率上緣走線 y
YR = 0.7                 # 迴流線 y

# 電池正極 -> shunt -> 分岔點
wire(ax, [(3.5, YP), (A, YP)])
ax.add_patch(Rectangle((A, YP - 0.24), B - A, 0.48, fc='white', ec=PWR, lw=2.2, zorder=4))
lbl(ax, (A + B) / 2, YP + 0.62, '$R_{shunt}$ 10 mΩ', fs=10.5, color=PWR, weight='bold')
lbl(ax, 5.2, 10.05, 'Kelvin（四線）差動量測\n量測線緊貼 shunt 兩端，不與功率走線共用', fs=9, color='#777')
node(ax, A, YP); node(ax, B, YP)
wire(ax, [(B, YP), (9.5, YP)])
node(ax, 9.5, YP)

# 兩條路徑：充電（上）／放電（下）
wire(ax, [(9.5, YP), (9.5, 10.4), (10.2, 10.4)])
wire(ax, [(9.5, YP), (9.5, 6.8), (10.2, 6.8)])
box(ax, 12.3, 10.4, 4.2, 1.0, [('IT6302 直流電源（CC-CV）', True, 9.5)], 'inst')
box(ax, 12.3, 6.8, 4.2, 1.0, [('IT8512A+ 電子負載（CC）', True, 9.5)], 'inst')
lbl(ax, 8.9, 9.75, '充電\n路徑', fs=9.5, color=PWR)
lbl(ax, 8.9, 7.45, '放電\n路徑', fs=9.5, color=PWR)
lbl(ax, 12.3, 8.60, '軟體互鎖\n任一時刻僅一條路徑帶電', fs=9, color='#777')

# 迴流：兩儀器 -> 右側匯流 -> 電池負極
wire(ax, [(14.4, 10.4), (14.9, 10.4), (14.9, YR), (3.5, YR), (3.5, 7.4)], color=RTN, lw=2.6)
wire(ax, [(14.4, 6.8), (14.9, 6.8)], color=RTN, lw=2.6)

# 單點共地
node(ax, 5.0, YR, color=RTN)
for i, hw in enumerate([0.44, 0.28, 0.14]):
    ax.plot([5.0 - hw, 5.0 + hw], [YR - 0.28 - i * 0.16] * 2, color=RTN, lw=2.0, zorder=5)
ax.plot([5.0, 5.0], [YR, YR - 0.28], color=RTN, lw=2.0, zorder=5)
lbl(ax, 5.85, YR - 0.55, '單點共地（電池負極就近接出）', fs=9.5, color='#555', ha='left')

# ---------------- 量測與通訊（下半部） ----------------
box(ax, 6.2, 3.5, 3.3, 1.7,
    [('INA226', True, 11.5), ('電流／電壓量測', False, 9.5), ('I²C 位址 0x40', False, 9)], 'inst')
box(ax, 12.1, 3.5, 3.4, 1.7,
    [('STM32G071', True, 11.5), ('嵌入式估測標的', False, 9.5)], 'mcu')
box(ax, 12.1, 1.5, 3.4, 0.9, [('上位機（排程·紀錄）', True, 9.5)], 'host')

# Kelvin 四線：VBUS／IN+／IN−
arrow(ax, (4.7, 4.35), (4.7, YP - 0.08))
arrow(ax, (A, 4.35), (A, YP - 0.26))
arrow(ax, (B, 4.35), (B, YP - 0.26))
lbl(ax, 4.55, 6.5, 'VBUS', fs=9.5, color=SIG, ha='right')
lbl(ax, 5.88, 6.5, 'IN+', fs=9.5, color=SIG, ha='left')
lbl(ax, 7.62, 6.5, 'IN-', fs=9.5, color=SIG, ha='left')

# INA226 接地
wire(ax, [(5.0, 2.65), (5.0, YR)], color=RTN, lw=1.6, ls='--')

# I²C 與回報
arrow(ax, (7.85, 3.5), (10.4, 3.5))
lbl(ax, 9.12, 3.88, 'I²C1 @ 400 kHz', fs=9, color=SIG)
arrow(ax, (12.1, 2.65), (12.1, 1.95))
lbl(ax, 10.2, 2.30, 'USB-CDC 每秒回報', fs=9, color=SIG, ha='right')

fig.tight_layout()
fig.savefig(OUT / 'fig3-2.png', dpi=200, bbox_inches='tight', pad_inches=0.10, facecolor='white')
plt.close(fig)
print('saved fig3-2.png')
