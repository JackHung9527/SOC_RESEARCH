# -*- coding: utf-8 -*-
"""產生圖 3-4 韌體骨架與三種 SOC 估測方法之掛載關係（正式方塊圖）。

風格比照 _gen_ch3_arch.py（圖 3-1）；本機（樹莓派）無 Microsoft JhengHei，
以 Noto Sans CJK TC 替代（同為黑體系，視覺一致）。
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager

OUT = Path(__file__).resolve().parent
CJK = 'Microsoft JhengHei'
if not any(f.name == CJK for f in font_manager.fontManager.ttflist):
    CJK = 'Noto Sans CJK TC'
plt.rcParams['font.family'] = CJK
plt.rcParams['axes.unicode_minus'] = False
ARROW = '#5A5A5A'; TXT = '#1A1A1A'
S = {'host': dict(fc='#2E5C9A', ec='#1F3864', tc='white'),
     'inst': dict(fc='#DCE6F4', ec='#2E5C9A', tc=TXT),
     'mcu':  dict(fc='#E2EFDA', ec='#548235', tc=TXT),
     'mcuin': dict(fc='white', ec='#548235', tc=TXT)}


def box(ax, cx, cy, w, h, lines, kind, lw=1.9):
    st = S[kind]
    ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                 boxstyle='round,pad=0.02,rounding_size=0.10',
                 fc=st['fc'], ec=st['ec'], lw=lw))
    n = len(lines)
    for i, (t, b, fs) in enumerate(lines):
        yy = cy + (n-1)/2*0.40 - i*0.40
        ax.text(cx, yy, t, ha='center', va='center', family=CJK,
                fontsize=fs, fontweight=('bold' if b else 'normal'), color=st['tc'])


def arrow(ax, p1, p2, label=None, lpos=None):
    """lpos：標籤絕對座標。規則：標籤一律離箭頭線與方塊邊 ≥0.3 單位，不可壓線。"""
    ax.annotate('', xy=p2, xytext=p1, arrowprops=dict(arrowstyle='-|>', color=ARROW,
                lw=1.8, shrinkA=2, shrinkB=2, mutation_scale=15))
    if label:
        ax.text(lpos[0], lpos[1], label, ha='center', va='center', family=CJK,
                fontsize=9.5, color='#666')


fig, ax = plt.subplots(figsize=(8.6, 6.0), dpi=200)
ax.set_xlim(0, 13.4); ax.set_ylim(0, 9); ax.axis('off')

# ---- 上層：初始化 / 節拍 / 主迴圈 ----
box(ax, 2.2, 7.9, 3.5, 1.35,
    [('開機初始化（一次）', True, 11.5), ('通訊埠·量測晶片·校正載入', False, 9.5)], 'inst')
box(ax, 2.2, 5.7, 3.5, 1.35,
    [('系統節拍', True, 12), ('百微秒計時器·只計數', False, 9.5)], 'inst')
box(ax, 7.0, 6.8, 3.9, 1.5,
    [('主迴圈（反覆執行）', True, 12.5), ('依節拍分派週期性事件', False, 10)], 'host')

arrow(ax, (3.95, 7.9), (5.6, 7.25), '完成後進入', lpos=(4.85, 7.98))
arrow(ax, (3.95, 5.7), (5.6, 6.35), '累計節拍', lpos=(4.45, 6.62))

# ---- 下層：每秒量測—估測—回報管線 ----
box(ax, 1.9, 3.0, 2.9, 1.4,
    [('電池量測', True, 11.5), ('INA226 電壓／電流', False, 9.5)], 'inst')
box(ax, 5.05, 3.0, 2.7, 1.4,
    [('校正套用', True, 11.5), ('多點線性內插', False, 9.5)], 'inst')

# SOC 估測容器（第四章掛載點，綠色）
gc, gy, gw, gh = 8.75, 2.75, 3.3, 3.3
box(ax, gc, gy, gw, gh, [], 'mcu')
ax.text(gc, gy+gh/2-0.38, 'SOC 估測模組', ha='center', va='center',
        family=CJK, fontsize=11.5, fontweight='bold', color=TXT)
for i, name in enumerate(['庫倫計數（4.1）', '擴展卡爾曼濾波（4.2）', '動態阻抗（4.3）']):
    box(ax, gc, gy+0.62-i*0.78, gw-0.6, 0.62, [(name, False, 10)], 'mcuin', lw=1.4)
ax.text(gc, gy-gh/2-0.32, '第四章三法之共同掛載點·各自獨立開關（4.4.3 資源量測）',
        ha='center', va='center', family=CJK, fontsize=9, color='#666')

box(ax, 12.15, 3.0, 2.1, 1.4,
    [('狀態回報', True, 11.5), ('序列埠·每秒一行', False, 9.5)], 'inst')

# 主迴圈 → 管線（每秒觸發）
arrow(ax, (6.2, 6.05), (2.3, 3.7), '每秒觸發', lpos=(5.05, 4.75))
# 管線串接
arrow(ax, (3.35, 3.0), (3.7, 3.0))
arrow(ax, (6.4, 3.0), (7.1, 3.0))
arrow(ax, (10.4, 3.0), (11.1, 3.0))

fig.tight_layout()
fig.savefig(OUT / 'fig3-4.png', dpi=200, bbox_inches='tight', pad_inches=0.08, facecolor='white')
plt.close(fig)
print('saved fig3-4.png')
