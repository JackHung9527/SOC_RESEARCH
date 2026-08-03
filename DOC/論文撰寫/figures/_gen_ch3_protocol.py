# -*- coding: utf-8 -*-
"""產生圖 3-5 跨輪自動化測試協定流程圖。

風格比照 _gen_ch3_arch.py／_gen_ch4_figs.py：圓角框為步驟、菱形為判斷、
斜角框為紀錄；右側掛說明卡（x >= 8.7，與主流程框完全不重疊）。
標籤一律絕對定位，離線離框 >= 0.25 單位，不得壓線。
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from matplotlib import font_manager

OUT = Path(__file__).resolve().parent
CJK = 'Microsoft JhengHei'
if not any(f.name == CJK for f in font_manager.fontManager.ttflist):
    CJK = 'Noto Sans CJK TC'
plt.rcParams['font.family'] = CJK
plt.rcParams['axes.unicode_minus'] = False

TXT = '#1A1A1A'
ARROW = '#5A5A5A'
LOOP = '#BF9000'
NEXT = '#2E5C9A'
S = {'start': dict(fc='#2E5C9A', ec='#1F3864', tc='white'),
     'step':  dict(fc='#DCE6F4', ec='#2E5C9A', tc=TXT),
     'dis':   dict(fc='#FCE4D6', ec='#C55A11', tc=TXT),
     'rec':   dict(fc='#E2EFDA', ec='#548235', tc=TXT),
     'note':  dict(fc='#FFF9E6', ec='#BF9000', tc=TXT),
     'dec':   dict(fc='#FFF2CC', ec='#BF9000', tc=TXT)}

X = 5.4          # 主流程中軸
CX = 10.5        # 說明卡中軸（左緣 8.7，主流程最寬框右緣 8.4）


def box(ax, cx, cy, w, h, lines, kind, lw=1.9):
    st = S[kind]
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                 boxstyle='round,pad=0.02,rounding_size=0.10',
                 fc=st['fc'], ec=st['ec'], lw=lw, zorder=3))
    n = len(lines)
    for i, (t, b, fs) in enumerate(lines):
        yy = cy + (n - 1) / 2 * 0.36 - i * 0.36
        ax.text(cx, yy, t, ha='center', va='center', family=CJK, zorder=4,
                fontsize=fs, fontweight=('bold' if b else 'normal'), color=st['tc'])


def diamond(ax, cx, cy, w, h, text, fs=10.5):
    st = S['dec']
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)],
                 closed=True, fc=st['fc'], ec=st['ec'], lw=1.9, zorder=3))
    ax.text(cx, cy, text, ha='center', va='center', family=CJK, fontsize=fs,
            color=st['tc'], zorder=4)


def rec(ax, cx, cy, w, h, lines):
    st = S['rec']
    sk = 0.34
    ax.add_patch(Polygon([(cx - w / 2 + sk, cy + h / 2), (cx + w / 2, cy + h / 2),
                          (cx + w / 2 - sk, cy - h / 2), (cx - w / 2, cy - h / 2)],
                 closed=True, fc=st['fc'], ec=st['ec'], lw=1.9, zorder=3))
    n = len(lines)
    for i, (t, b, fs) in enumerate(lines):
        yy = cy + (n - 1) / 2 * 0.34 - i * 0.34
        ax.text(cx, yy, t, ha='center', va='center', family=CJK, zorder=4,
                fontsize=fs, fontweight=('bold' if b else 'normal'), color=st['tc'])


def arrow(ax, p1, p2, color=ARROW, lw=1.8, ls='-'):
    ax.annotate('', xy=p2, xytext=p1, zorder=2,
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, ls=ls,
                                shrinkA=0, shrinkB=0, mutation_scale=15))


def path(ax, pts, color=ARROW, lw=1.8, ls='-'):
    for i in range(len(pts) - 2):
        ax.plot([pts[i][0], pts[i + 1][0]], [pts[i][1], pts[i + 1][1]],
                color=color, lw=lw, ls=ls, zorder=2, solid_capstyle='round')
    arrow(ax, pts[-2], pts[-1], color=color, lw=lw, ls=ls)


def lbl(ax, x, y, t, fs=9.5, color='#666', ha='center'):
    ax.text(x, y, t, ha=ha, va='center', family=CJK, fontsize=fs, color=color, zorder=6)


fig, ax = plt.subplots(figsize=(7.2, 8.55), dpi=200)
ax.set_xlim(0, 12.6); ax.set_ylim(-0.5, 16.0); ax.axis('off')

# ---- 主流程節點 ----
box(ax, X, 15.2, 8.0, 0.95,
    [('開始一輪：讀回既有紀錄，續接輪次／週期編號與累積 Ah', True, 10)], 'start')
box(ax, X, 13.85, 8.0, 0.95,
    [('設定放電倍率序列 k = 1…4：0.5C／1.0C／1.5C／2.0C', True, 10)], 'step')
box(ax, X, 12.4, 5.0, 1.05,
    [('充電步（固定 0.5C）', True, 11), ('CC-CV 定電流—定電壓', False, 9.5)], 'step')
diamond(ax, X, 10.75, 4.4, 1.5, '$V \\geq V_{cv}$ 且 $I \\leq 0.1C$ ？')
box(ax, X, 9.15, 4.4, 0.9, [('休息 30 分（開路鬆弛）', True, 10.5)], 'step')
box(ax, X, 7.6, 5.4, 1.25,
    [('放電步：CC @ 第 k 個倍率', True, 11), ('每 60 s 注入一次 dV/dI 擾動', False, 9.5)], 'dis')
diamond(ax, X, 5.95, 4.0, 1.4, '$V \\leq V_{cut}$ ？')
rec(ax, X, 4.35, 6.4, 1.25,
    [('追加一列至跨輪紀錄檔', True, 10.5), ('週期／輪次／方向／倍率／Ah／保持率／累積 Ah', False, 8.5)])
box(ax, X, 2.95, 4.4, 0.9, [('休息 30 分', True, 11)], 'step')
diamond(ax, X, 1.55, 3.4, 1.3, 'k < 4 ？')
box(ax, X, 0.05, 5.0, 0.85,
    [('一輪完成（約 16～18 h）', True, 10.5)], 'rec')

# ---- 主幹箭頭 ----
arrow(ax, (X, 14.72), (X, 14.33))
arrow(ax, (X, 13.38), (X, 12.93))
arrow(ax, (X, 11.87), (X, 11.50))
arrow(ax, (X, 10.00), (X, 9.60))
arrow(ax, (X, 8.70), (X, 8.23))
arrow(ax, (X, 6.98), (X, 6.65))
arrow(ax, (X, 5.25), (X, 4.98))
arrow(ax, (X, 3.72), (X, 3.40))
arrow(ax, (X, 2.50), (X, 2.20))
arrow(ax, (X, 0.90), (X, 0.48))
lbl(ax, X + 0.22, 9.82, '是', ha='left')
lbl(ax, X + 0.22, 5.12, '是', ha='left')
lbl(ax, X + 0.22, 0.70, '否', ha='left')

# ---- 判斷「否」的自迴圈（回到同一步）----
path(ax, [(X - 2.2, 10.75), (2.35, 10.75), (2.35, 12.55), (X - 2.5, 12.55)], color=LOOP)
lbl(ax, 2.60, 11.15, '否（繼續充電）', color=LOOP, ha='left')
path(ax, [(X - 2.0, 5.95), (2.35, 5.95), (2.35, 7.75), (X - 2.7, 7.75)], color=LOOP)
lbl(ax, 2.60, 6.35, '否（繼續放電）', color=LOOP, ha='left')

# ---- k < 4：回到充電步，進入下一個倍率 ----
path(ax, [(X - 1.7, 1.55), (1.05, 1.55), (1.05, 12.25), (X - 2.5, 12.25)], color=NEXT)
lbl(ax, 1.30, 2.15, '是：k ← k + 1\n換下一個放電倍率', color=NEXT, ha='left', fs=9)

# ---- 右側說明卡（左緣 8.7，與主流程無交疊）----
box(ax, CX, 12.55, 3.6, 1.5,
    [('充電一律 0.5C', True, 10.5), ('高倍率充電會傷害電池', False, 9.5),
     ('並污染健康度基準', False, 9.5)], 'note')
arrow(ax, (7.95, 12.4), (8.65, 12.55), color=LOOP, lw=1.3, ls='--')

box(ax, CX, 7.6, 3.6, 2.35,
    [('dV/dI 擾動子流程', True, 10.5), ('由基礎倍率步降至 0.2C', False, 9.5),
     ('停留 1 秒後步回原倍率', False, 9.5), ('取步降前後兩穩態樣本', False, 9.5),
     ('算 ΔV/ΔI 得該 SOC 的動態阻抗', False, 9.5), ('庫倫計數涵蓋擾動秒數', False, 9.5)], 'note')
arrow(ax, (8.15, 7.6), (8.65, 7.6), color=LOOP, lw=1.3, ls='--')

box(ax, CX, 4.35, 3.6, 1.15,
    [('週期編號於放電至截止時遞增', False, 9.5), ('充電繼承其後放電之編號', False, 9.5)], 'note')
arrow(ax, (8.42, 4.35), (8.65, 4.35), color=LOOP, lw=1.3, ls='--')

fig.tight_layout()
fig.savefig(OUT / 'fig3-5.png', dpi=200, bbox_inches='tight', pad_inches=0.10, facecolor='white')
plt.close(fig)
print('saved fig3-5.png')
