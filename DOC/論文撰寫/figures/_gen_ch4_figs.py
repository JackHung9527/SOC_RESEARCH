# -*- coding: utf-8 -*-
"""產生第四章方塊圖（演算法流程）為 PNG。高階呈現，不放韌體實作細節。
   圖 4-1 庫倫計數流程 / 圖 4-2 EKF 預測-更新遞迴 / 圖 4-3 動態阻抗離線建表+即時估測。
   （圖 4-4 動態阻抗實測擬合由 dynz_fit.py 產生）"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent
CJK = 'Microsoft JhengHei'
plt.rcParams['font.family'] = CJK
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['axes.unicode_minus'] = False

STYLE = {
    'start':  dict(fc='#FCE4D6', ec='#C55A11'),
    'process':dict(fc='#DCE6F4', ec='#2E5C9A'),
    'data':   dict(fc='#E2EFDA', ec='#548235'),
    'output': dict(fc='#FFF2CC', ec='#BF9000'),
    'phase':  dict(fc='#2E5C9A', ec='#1F3864'),
}
TXT = '#1A1A1A'; ARROW = '#5A5A5A'; NOTE = '#6A6A6A'
UNIT = 0.80; HDR_FS = 12.5; EQ_FS = 12; NOTE_FS = 10; PHASE_FS = 12.5


def _h(st):
    n = (1 if st.get('h') else 0) + len(st.get('m', []))
    return 0.62 if st['kind'] == 'phase' else 0.42 + 0.46 * max(n, 1)


def render(path, stages, loops=None, box_w=4.4, cx=3.0, xlim=(0.0, 9.8),
           top_pad=0.35, bot_pad=0.30, gap=0.72):
    heights = [_h(s) for s in stages]
    total = sum(heights) + gap * (len(stages) - 1) + top_pad + bot_pad
    fig, ax = plt.subplots(figsize=((xlim[1]-xlim[0])*UNIT, total*UNIT), dpi=200)
    ax.set_xlim(*xlim); ax.set_ylim(0, total); ax.axis('off')
    centers = []
    y = total - top_pad
    for st, h in zip(stages, heights):
        cy = y - h/2; centers.append(cy)
        w = (xlim[1]-xlim[0]-0.5) if st['kind'] == 'phase' else box_w
        bx = (xlim[0]+0.25) if st['kind'] == 'phase' else (cx - w/2)
        sty = STYLE[st['kind']]
        ax.add_patch(FancyBboxPatch((bx, cy-h/2+0.06), w, h-0.12,
                     boxstyle='round,pad=0.02,rounding_size=0.14',
                     fc=sty['fc'], ec=sty['ec'], lw=1.8, mutation_aspect=1.0))
        if st['kind'] == 'phase':
            ax.text((xlim[0]+xlim[1])/2, cy, st['h'], ha='center', va='center',
                    family=CJK, fontsize=PHASE_FS, fontweight='bold', color='white')
        else:
            lines = ([('cjk', st['h'])] if st.get('h') else []) + [('math', m) for m in st.get('m', [])]
            line_h = (h-0.30)/len(lines)
            y0 = cy + (len(lines)-1)/2.0*line_h
            for i, (kind, txt) in enumerate(lines):
                yy = y0 - i*line_h
                if kind == 'cjk':
                    ax.text(cx, yy, txt, ha='center', va='center', family=CJK,
                            fontsize=HDR_FS, fontweight='bold', color=TXT)
                else:
                    ax.text(cx, yy, txt, ha='center', va='center', fontsize=EQ_FS, color=TXT)
            for li, ntxt in st.get('side', []):
                ax.text(cx + w/2 + 0.18, y0 - li*line_h, ntxt, ha='left', va='center',
                        family=CJK, fontsize=NOTE_FS, color=NOTE)
        y = y - h - gap
    # arrows
    for i in range(len(stages)-1):
        y1 = centers[i] - heights[i]/2 + 0.06
        y2 = centers[i+1] + heights[i+1]/2 - 0.06
        ax.annotate('', xy=(cx, y2), xytext=(cx, y1),
                    arrowprops=dict(arrowstyle='-|>', color=ARROW, lw=1.9, shrinkA=0, shrinkB=0, mutation_scale=16))
        lbl = stages[i+1].get('in_label')
        if lbl:
            ax.text(cx+0.18, (y1+y2)/2, lbl, ha='left', va='center', family=CJK, fontsize=NOTE_FS, color=NOTE)
    # feedback loop: route orthogonally on the far right, horizontal label
    for (fi, ti, lbl) in (loops or []):
        x_edge = cx + box_w/2
        xr = x_edge + 0.95
        yf = centers[fi]; yt = centers[ti]
        ax.plot([x_edge, xr], [yf, yf], color=ARROW, lw=1.7, solid_capstyle='round')
        ax.plot([xr, xr], [yf, yt], color=ARROW, lw=1.7, solid_capstyle='round')
        ax.annotate('', xy=(x_edge, yt), xytext=(xr, yt),
                    arrowprops=dict(arrowstyle='-|>', color=ARROW, lw=1.7, shrinkA=0, shrinkB=0, mutation_scale=14))
        ax.text(xr+0.14, (yf+yt)/2, lbl, ha='left', va='center', family=CJK, fontsize=NOTE_FS, color=NOTE)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(path, dpi=200, bbox_inches='tight', pad_inches=0.06, facecolor='white')
    plt.close(fig)
    print('saved', Path(path).name)


# ── 圖 4-1 庫倫計數 SOC 更新流程 ──
render(OUT / 'fig4-1.png', [
    {'kind': 'start',  'h': '每秒觸發一次', 'm': []},
    {'kind': 'process','h': '讀取電流', 'm': [r'$I_k$'], 'side': [(0, '經校正，放電為正')]},
    {'kind': 'process','h': '累計用掉的電量',
        'm': [r'$\Delta q = I_k \times \Delta t$', r'$q \leftarrow q + \Delta q$']},
    {'kind': 'process','h': '換算為 SOC',
        'm': [r'$SOC = 1 - q / q_{rated}$'], 'side': [(1, '限制在 0~100%')]},
    {'kind': 'output', 'h': '輸出 SOC', 'm': [r'$SOC_k$']},
], box_w=4.6, cx=3.0, xlim=(0.0, 8.4))

# ── 圖 4-2 EKF 預測—更新遞迴 ──
render(OUT / 'fig4-2.png', [
    {'kind': 'process','h': '時間更新（預測）',
        'm': [r'$x^{-} = A\,\hat{x} + B\,I_k$', r'$P^{-} = A\,P\,A^{T} + Q$']},
    {'kind': 'process','h': '量測更新（以端電壓修正）',
        'm': [r'$\hat{y} = OCV(SOC) - I_k R_0 - V_1$',
              r'$C = [\,\partial OCV/\partial SOC,\ -1\,]$',
              r'$S = C\,P^{-}C^{T} + R$',
              r'$K = P^{-}C^{T} / S$',
              r'$\hat{x} = x^{-} + K\,(V_{meas} - \hat{y})$',
              r'$P = (I - K\,C)\,P^{-}$']},
    {'kind': 'output', 'h': '輸出 SOC', 'm': [r'$SOC_k = \mathrm{clamp}(\hat{x}.SOC)$']},
], loops=[(2, 0, '下一週期\n（每秒）')], box_w=5.2, cx=3.0, xlim=(0.0, 8.6))

# ── 圖 4-3 動態阻抗 離線建表 + 即時估測 ──
render(OUT / 'fig4-3.png', [
    {'kind': 'phase',  'h': '離線建表（在電腦上做一次）', 'm': []},
    {'kind': 'process','h': '逐擾動事件算動態阻抗',
        'm': [r'$Z = \Delta V/\Delta I = (V_1-V_2)/(I_1-I_2)$'],
        'side': [(0, '配對該時刻的 SOC')]},
    {'kind': 'process','h': '擬合二次曲線',
        'm': [r'$Z = a\,SOC^{2} + b\,SOC + c$'],
        'in_label': '累積散點 (SOC, Z)', 'side': [(1, r'最低點約在 SOC 50%')]},
    {'kind': 'data',   'h': '把係數存入晶片', 'm': [r'$a,\ b,\ c$']},
    {'kind': 'phase',  'h': '即時估測（晶片上）', 'm': []},
    {'kind': 'process','h': '偵測擾動、解二次式',
        'm': [r'$a\,SOC^{2} + b\,SOC + (c - Z) = 0$'], 'side': [(0, '得兩個解')]},
    {'kind': 'output', 'h': '挑出正確解，輸出 SOC',
        'm': [r'$SOC_k$'], 'in_label': '依曲線位置挑唯一解'},
], box_w=6.2, cx=3.4, xlim=(0.0, 9.6))

print('done (fig4-1, fig4-2, fig4-3)')
