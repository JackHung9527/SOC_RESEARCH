# -*- coding: utf-8 -*-
"""Figure 1: test-platform system architecture (English block diagram)."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent
FONT = 'Times New Roman'
plt.rcParams['font.family'] = FONT
plt.rcParams['axes.unicode_minus'] = False
ARROW = '#5A5A5A'
TXT = '#1A1A1A'
S = {'host': dict(fc='#2E5C9A', ec='#1F3864', tc='white'),
     'inst': dict(fc='#DCE6F4', ec='#2E5C9A', tc=TXT),
     'mcu':  dict(fc='#E2EFDA', ec='#548235', tc=TXT),
     'dut':  dict(fc='#FFF2CC', ec='#BF9000', tc=TXT)}


def box(ax, cx, cy, w, h, lines, kind):
    st = S[kind]
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                 boxstyle='round,pad=0.02,rounding_size=0.10',
                 fc=st['fc'], ec=st['ec'], lw=1.9))
    n = len(lines)
    for i, (t, b, fs) in enumerate(lines):
        yy = cy + (n - 1) / 2 * 0.42 - i * 0.42
        ax.text(cx, yy, t, ha='center', va='center', family=FONT,
                fontsize=fs, fontweight=('bold' if b else 'normal'), color=st['tc'])


def arrow(ax, p1, p2, label=None, lx=0.12):
    ax.annotate('', xy=p2, xytext=p1, arrowprops=dict(arrowstyle='-|>', color=ARROW,
                lw=1.8, shrinkA=2, shrinkB=2, mutation_scale=15))
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx + lx, my, label, ha='left', va='center', family=FONT,
                fontsize=10.5, color='#555')


fig, ax = plt.subplots(figsize=(8.2, 6.0), dpi=200)
ax.set_xlim(0, 12)
ax.set_ylim(0, 10)
ax.axis('off')

box(ax, 6.0, 9.0, 8.2, 1.0,
    [('Host PC  (scheduling / safety interlock / logging)', True, 13)], 'host')
box(ax, 2.3, 6.2, 3.2, 1.5,
    [('IT6302 DC Supply', True, 12), ('Charge path (CC-CV)', False, 11)], 'inst')
box(ax, 6.0, 6.2, 3.2, 1.5,
    [('IT8512A+ E-Load', True, 12), ('Discharge path (CC)', False, 11)], 'inst')
box(ax, 9.7, 6.2, 3.3, 1.5,
    [('STM32 + INA226', True, 12), ('Embedded estimator', False, 11)], 'mcu')
box(ax, 4.15, 2.8, 3.6, 1.4,
    [('DUT: Cell', True, 12.5), ('NMC 2000 mAh', False, 11)], 'dut')

# host -> instruments
arrow(ax, (2.3, 8.5), (2.3, 6.95), 'SCPI / USB')
arrow(ax, (6.0, 8.5), (6.0, 6.95), 'SCPI / USB')
arrow(ax, (9.7, 8.5), (9.7, 6.95), 'USB (status)')
# instruments -> DUT
arrow(ax, (2.6, 5.45), (3.6, 3.5), 'Charge')
arrow(ax, (5.7, 5.45), (4.7, 3.5), 'Discharge')
# DUT -> MCU / INA226 sensing
arrow(ax, (5.95, 2.8), (8.4, 5.45), 'V / I via 10 m$\\Omega$ shunt')

fig.tight_layout()
fig.savefig(OUT / 'fig_arch_en.png', dpi=200, bbox_inches='tight',
            pad_inches=0.08, facecolor='white')
plt.close(fig)
print('saved fig_arch_en.png')
