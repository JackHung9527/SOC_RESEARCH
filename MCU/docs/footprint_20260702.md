# 三法嵌入式 footprint 量測（2026-07-02）

量測方式：`make EXTRA_CFLAGS=-DSOC_*_ENABLE=…` 產生骨架／骨架＋單一方法變體，
以 `arm-none-eabi-size` 取 text/data/bss；淨佔用 = 變體 − base。
工具鏈與最佳化同 project.yaml（arm-none-eabi-gcc, -Og）。
每次更新 CPU cycles 由韌體 1 Hz soc 狀態行 `(NNNcyc)` 實測（perf_cyc）。

| 變體 | text | data | bss | Flash (text+data) | RAM (data+bss) | ΔFlash | ΔRAM |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 60448 | 492 | 4348 | 60940 | 4840 | — | — |
| coulomb | 61572 | 492 | 4368 | 62064 | 4860 | +1124 | +20 |
| ekf | 62316 | 492 | 4388 | 62808 | 4880 | +1868 | +40 |
| zdyn | 61900 | 496 | 4392 | 62396 | 4888 | +1456 | +48 |
| full | 64348 | 496 | 4448 | 64844 | 4944 | +3904 | +104 |

> 註：EKF 之 ΔFlash 含 OCV 對照表；EKF/動態阻抗牽入之軟浮點程式庫
> （__aeabi_f*）若骨架其他處已使用則不重複計入——此即「同編譯設定、
> 同骨架」相減法的量測語意（論文 4.4.3）。
