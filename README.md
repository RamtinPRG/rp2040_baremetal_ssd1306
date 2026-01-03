# SSD1306 OLED Driver (RP2040, Bare-Metal Assembly)

## Overview

This project implements a **bare-metal SSD1306 OLED driver** written entirely in **ARM Thumb assembly** for the **RP2040 (Cortex-M0+)**.  
It configures **I2C0 directly via registers** (DW_apb_i2c) without using high-level SDK drivers.

The program:

- Initializes GPIOs and pads for I2C
- Configures I2C0 in **master fast-mode (~400 kHz)**
- Sends the SSD1306 initialization command sequence
- Transfers a full framebuffer to the display
- Runs indefinitely after initialization

No RTOS, no HAL abstractions, no C code in the data path.

---

## Target Hardware

- **MCU:** RP2040 (Cortex-M0+)
- **Board:** Any RP2040-based board
- **OLED Display:** SSD1306 (I2C)
- **OLED Resolution:** 128 * 64
- **I2C Address:** `0x3C`
- **I2C Instance:** I2C0

---

## Pin Configuration

| Signal | GPIO | Notes |
|------|------|------|
| SDA  | GPIO12 | I2C0 SDA |
| SCL  | GPIO13 | I2C0 SCL |

Internal pull-ups are enabled via `PADS_BANK0`.

---

## Software Environment

The demo uses `RP2040 C/C++ SDK` even though it doesn't use other functionalities of the SDK other than `stdio` for ease of debugging purposes.

There is a C demo code as well. If you are going to intend to run the C code, change the executable source in CMakeLists.txt.

To compile and run the project you simply do the same steps as a typical RP2040 C/C++ SDK project.

## I2C Implementation Details

- Peripheral: **DW_apb_i2c**
- Mode: Master
- Speed: Fast-mode (~400 kHz)
- FIFO polling (no interrupts, no DMA usage)
- Bus idle detection via `IC_STATUS.MST_ACTIVITY`

### Important Registers Used

| Register      | Purpose               |
| ------------- | --------------------- |
| `IC_CON`      | Control configuration |
| `IC_TAR`      | Target slave address  |
| `IC_DATA_CMD` | Transmit FIFO         |
| `IC_STATUS`   | FIFO and bus status   |
| `IC_ENABLE`   | Peripheral enable     |

---

## SSD1306 Protocol Notes

- Commands are sent using control byte `0x80`
- Framebuffer data is sent using control byte `0x40`
- Column and page addressing is set before buffer transfer
- Full framebuffer size: `8 pages × 128 columns = 1024 bytes`

---

## Functions

### `main`

- Releases I2C0 from reset
- Configures GPIOs and pads
- Initializes I2C peripheral
- Sends SSD1306 init sequence
- Sends framebuffer
- Enters infinite loop

---

### `i2c_write_buf`

```text
r0 = buffer address
r1 = buffer length
```

Blocking I2C write routine using FIFO polling.

---

### `send_ssd1306_cmd`

```text
r0 = command byte
```

Sends a single SSD1306 command.

---

### `send_ssd1306_cmd_list`

```text
r0 = command list address
r1 = list length
```

Sends multiple SSD1306 commands sequentially.

---

### `send_ssd1306_buffer`

```text
r0 = framebuffer address
r1 = framebuffer length
```

Configures addressing and sends full display buffer.

---

## References

- [RP2040 Datasheet](https://pip-assets.raspberrypi.com/categories/814-rp2040/documents/RP-008371-DS-1-rp2040-datasheet.pdf?disposition=inline)
- [SSD1306 Datasheet](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf)
