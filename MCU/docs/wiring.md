# 詳細接線清單與訊號定義

## 1. STM32G071RB 腳位配置

| 腳位  | 功能       | 方向 | 連接對象           | 備註                        |
|-------|------------|------|--------------------|-----------------------------|
| PB8   | I2C1_SCL   | OD   | INA226 SCL         | AF6, 4.7 kΩ pull-up → 3.3V  |
| PB9   | I2C1_SDA   | OD   | INA226 SDA         | AF6, 4.7 kΩ pull-up → 3.3V  |
| PA2   | USART2_TX  | PP   | ST-Link VCP RX     | AF1, 115200/8N1             |
| PA3   | USART2_RX  | IN   | ST-Link VCP TX     | AF1                         |
| PA5   | GPIO_OUT   | PP   | LD2 (使用者 LED)    | 心跳指示                    |
| PA10  | GPIO_EXTI  | IN   | INA226 ALERT       | EXTI10, 上升／下降緣        |
| PC13  | GPIO_EXTI  | IN   | B1 (使用者按鈕)     | 觸發單次量測               |

> OD = Open-Drain, PP = Push-Pull, IN = Input, AF = Alternate Function

## 2. INA226 模組腳位

| 腳位   | 接到            | 說明                                    |
|--------|-----------------|-----------------------------------------|
| VS     | 3.3V            | 邏輯與類比共用供電（2.7 ~ 5.5 V）       |
| GND    | GND             | 系統共地                                |
| IN+    | Rshunt 高側     | shunt 高電位端，亦即電池正極端          |
| IN-    | Rshunt 低側     | shunt 低電位端，接外部負載／電源        |
| VBUS   | Cell+           | 母線電壓量測端（0 ~ 36 V）              |
| ALERT  | PA10            | 開汲極輸出，需外接 10 kΩ pull-up        |
| SCL    | PB8             | I2C 時脈                                |
| SDA    | PB9             | I2C 資料                                |
| A0     | GND             | 位址選擇 bit0                           |
| A1     | GND             | 位址選擇 bit1                           |

A0/A1 接 GND → 7-bit slave address = `0x40`。

## 3. 量測迴路（高功率側）

```
   Cell+ ──┬─────────────► VBUS+ ──► IT6302 / IT8512A+
           │                         (DC 源／負載)
           │
           ●────────────► IN+ (INA226)
           │
           ●────────────► VBUS (INA226, 量測電池端點電壓)
           │
        Rshunt = 10 mΩ
           │
           ●────────────► IN- (INA226)
           │
   Cell- ──┴─────────────► VBUS- (與 GND 隔離，
                                   建議用差動量測)
```

> **重要**：高功率迴路與 INA226 邏輯地之間僅在單點共地，
> 避免 shunt 上的壓降耦合進邏輯供電。建議 INA226 GND
> 從電池負極端就近單點接出。

## 4. 訊號完整性建議

- I2C trace 長度 < 30 cm；超過時需縮短或加 buffer
- INA226 IN+/IN- 走 Kelvin 連接（4-wire），緊貼 Rshunt 兩個量測端子
- 電池正極端與 IN+ 之間的 trace 越短越好（< 5 cm），降低共模誤差
- 板邊附 100 µF 鋁質電容 + 0.1 µF 陶瓷做電源 bulk 與去耦
