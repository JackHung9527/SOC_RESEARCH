# -*- coding: utf-8 -*-
"""產生第二章等效電路模型圖（內阻 / 戴維寧 1-RC / 二階 2-RC）為 PNG。"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

OUT = Path(__file__).resolve().parent
CJK = 'Microsoft JhengHei'
plt.rcParams['font.family'] = CJK
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['axes.unicode_minus'] = False
WIRE = '#222222'; RFILL = '#DCE6F4'; REDGE = '#2E5C9A'


def wire(ax, pts, lw=1.6):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.plot(xs, ys, color=WIRE, lw=lw, solid_capstyle='round', zorder=2)


def resistor(ax, x, y, label, w=0.9, h=0.34):
    ax.add_patch(Rectangle((x - w/2, y - h/2), w, h, fc=RFILL, ec=REDGE, lw=1.6, zorder=3))
    ax.text(x, y, label, ha='center', va='center', fontsize=12, zorder=4)


def cap(ax, x, y, label):
    # two plates (vertical), wires on both sides on a horizontal branch
    g = 0.07; ph = 0.18
    ax.plot([x-g, x-g], [y-ph, y+ph], color=WIRE, lw=2.0, zorder=3)
    ax.plot([x+g, x+g], [y-ph, y+ph], color=WIRE, lw=2.0, zorder=3)
    ax.text(x, y - 0.34, label, ha='center', va='center', fontsize=12, zorder=4)


def source(ax, x, y, label):
    ax.add_patch(Circle((x, y), 0.28, fc='white', ec=WIRE, lw=1.7, zorder=3))
    ax.text(x, y + 0.10, '+', ha='center', va='center', fontsize=13, zorder=4)
    ax.plot([x - 0.07, x + 0.07], [y - 0.11, y - 0.11], color=WIRE, lw=1.8, zorder=4)
    ax.text(x, y - 0.62, label, ha='center', va='center', fontsize=11.5, zorder=4)


def rc_block(ax, xl, xr, ytop, rlabel, clabel):
    yr = ytop + 0.42; yc = ytop - 0.42
    # upper branch (R)
    wire(ax, [(xl, ytop), (xl, yr), (xr, yr), (xr, ytop)])
    resistor(ax, (xl+xr)/2, yr, rlabel)
    # lower branch (C)
    wire(ax, [(xl, ytop), (xl, yc), ((xl+xr)/2 - 0.07, yc)])
    wire(ax, [((xl+xr)/2 + 0.07, yc), (xr, yc), (xr, ytop)])
    cap(ax, (xl+xr)/2, yc, clabel)


def draw_circuit(ax, yc, n_rc, title):
    ytop = yc + 0.0
    ybot = yc - 1.4
    x_src = 0.7
    # source (vertical, left side)
    wire(ax, [(x_src, ybot), (x_src, ytop - 0.28)])
    wire(ax, [(x_src, ytop + 0.28), (x_src, ytop)])
    source(ax, x_src, yc - 0.0 if False else (ytop + ybot)/2, r'$V_{OC}(SOC)$')
    # wait: place source circle between ytop and ybot on left rail
    # (handled above via source at midpoint)
    # R0
    wire(ax, [(x_src, ytop), (1.5, ytop)])
    resistor(ax, 1.95, ytop, r'$R_0$')
    x = 2.4
    # RC blocks
    for i in range(n_rc):
        xl = x + 0.3; xr = xl + 1.5
        wire(ax, [(x, ytop), (xl, ytop)])
        rc_block(ax, xl, xr, ytop, rf'$R_{i+1}$', rf'$C_{i+1}$')
        x = xr
    # to right terminal
    x_term = x + 0.9
    wire(ax, [(x, ytop), (x_term, ytop)])
    wire(ax, [(x_src, ybot), (x_term, ybot)])
    # terminal nodes (open circles) + Vt label
    ax.add_patch(Circle((x_term, ytop), 0.06, fc='white', ec=WIRE, lw=1.5, zorder=4))
    ax.add_patch(Circle((x_term, ybot), 0.06, fc='white', ec=WIRE, lw=1.5, zorder=4))
    ax.annotate('', xy=(x_term + 0.55, ytop), xytext=(x_term + 0.55, ybot),
                arrowprops=dict(arrowstyle='<->', color='#888888', lw=1.2))
    ax.text(x_term + 0.72, (ytop+ybot)/2, r'$V_t$', ha='left', va='center', fontsize=12.5)
    ax.text(-1.25, yc + 1.05, title, ha='left', va='bottom', fontsize=13, fontweight='bold')


fig, axes = plt.subplots(3, 1, figsize=(7.4, 8.6), dpi=200)
specs = [(0, '(a) 內阻模型'), (1, '(b) 戴維寧（一階 RC）模型'), (2, '(c) 二階 RC 模型')]
for ax, (n, title) in zip(axes, specs):
    ax.set_xlim(-1.5, 9.3); ax.set_ylim(-2.0, 1.7); ax.axis('off')
    ax.set_aspect('equal')
    draw_circuit(ax, 0.0, n, title)
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01, hspace=0.05)
fig.savefig(OUT / 'fig2-1.png', dpi=200, bbox_inches='tight', pad_inches=0.08, facecolor='white')
plt.close(fig)
print('saved fig2-1.png')
