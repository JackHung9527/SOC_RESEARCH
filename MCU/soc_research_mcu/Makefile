# =============================================================================
# Makefile for SOC_RESEARCH STM32G071RBTx firmware
#   - Toolchain : arm-none-eabi-gcc 12.2 (Debian)
#   - HAL       : vendored under Drivers/ (CMSIS + STM32G0xx_HAL_Driver)
#   - Output    : build/<TARGET>.{elf,bin,hex} + map + size
#   - Publish   : ../../BUILD/<TARGET>.{elf,bin,hex}  (firmware-project root)
#   - Flash     : `make flash` -> openocd via on-board ST-LINK/V2.1
#
# Layout: this Makefile lives at MCU/soc_research_mcu/Makefile. The CubeIDE
# project root is MCU/soc_research_mcu/ (folder name MUST equal the .ioc base
# name). MCU/ is just a category folder above it. Source paths (Core/, Drivers/,
# USER_CODE/, .ld) are relative to MCU/soc_research_mcu/; PUBLISH_DIR =
# ../../BUILD/ resolves to SOC_RESEARCH/BUILD/, matching project.yaml::
# build_out_dir = ./BUILD.
# =============================================================================

TARGET      = soc_research_mcu
DEBUG       = 1
OPT         = -Og

BUILD_DIR   = build
PUBLISH_DIR = ../../BUILD

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
C_SOURCES =                                                       \
  Core/Src/main.c                                                 \
  Core/Src/stm32g0xx_it.c                                         \
  Core/Src/syscalls.c                                             \
  USER_CODE/userCode.c                                            \
  USER_CODE/softwareTim.c                                         \
  USER_CODE/uart_debug/uart_debug.c                               \
  USER_CODE/i2c_bus/i2c_bus.c                                     \
  USER_CODE/ina226/ina226.c                                       \
  USER_CODE/battery_monitor/battery_monitor.c                     \
  USER_CODE/soc_soh_calc/soc_soh_calc.c                           \
  Drivers/CMSIS/Device/ST/STM32G0xx/Source/Templates/system_stm32g0xx.c \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal.c                \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_cortex.c         \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_dma.c            \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_dma_ex.c         \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_exti.c           \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_flash.c          \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_flash_ex.c       \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_gpio.c           \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_i2c.c            \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_i2c_ex.c         \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_pwr.c            \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_pwr_ex.c         \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_rcc.c            \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_rcc_ex.c         \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_tim.c            \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_tim_ex.c         \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_uart.c           \
  Drivers/STM32G0xx_HAL_Driver/Src/stm32g0xx_hal_uart_ex.c

ASM_SOURCES = Drivers/CMSIS/Device/ST/STM32G0xx/Source/Templates/gcc/startup_stm32g071xx.s

# ---------------------------------------------------------------------------
# Toolchain
# ---------------------------------------------------------------------------
PREFIX = arm-none-eabi-
CC     = $(PREFIX)gcc
AS     = $(PREFIX)gcc -x assembler-with-cpp
CP     = $(PREFIX)objcopy
SZ     = $(PREFIX)size
HEX    = $(CP) -O ihex
BIN    = $(CP) -O binary -S

# ---------------------------------------------------------------------------
# CPU / FPU
# ---------------------------------------------------------------------------
CPU    = -mcpu=cortex-m0plus
FPU    =
FLOAT-ABI =
MCU    = $(CPU) -mthumb $(FPU) $(FLOAT-ABI)

# ---------------------------------------------------------------------------
# Defines
# ---------------------------------------------------------------------------
C_DEFS = \
  -DUSE_HAL_DRIVER \
  -DSTM32G071xx

AS_DEFS =

# ---------------------------------------------------------------------------
# Includes
# ---------------------------------------------------------------------------
C_INCLUDES = \
  -ICore/Inc \
  -IUSER_CODE \
  -IUSER_CODE/uart_debug \
  -IUSER_CODE/i2c_bus \
  -IUSER_CODE/ina226 \
  -IUSER_CODE/battery_monitor \
  -IUSER_CODE/soc_soh_calc \
  -IDrivers/STM32G0xx_HAL_Driver/Inc \
  -IDrivers/STM32G0xx_HAL_Driver/Inc/Legacy \
  -IDrivers/CMSIS/Device/ST/STM32G0xx/Include \
  -IDrivers/CMSIS/Include

AS_INCLUDES =

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
CFLAGS  = $(MCU) $(C_DEFS) $(C_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections
ASFLAGS = $(MCU) $(AS_DEFS) $(AS_INCLUDES) $(OPT) -Wall -fdata-sections -ffunction-sections

ifeq ($(DEBUG), 1)
CFLAGS += -g -gdwarf-2
endif

# Generate dep info
CFLAGS += -MMD -MP -MF"$(@:%.o=%.d)"

# ---------------------------------------------------------------------------
# Linker
# ---------------------------------------------------------------------------
LDSCRIPT = STM32G071RBTX_FLASH.ld

LIBS = -lc -lm -lnosys
LIBDIR =
LDFLAGS = $(MCU) -specs=nano.specs -u _printf_float -T$(LDSCRIPT) $(LIBDIR) $(LIBS) \
          -Wl,-Map=$(BUILD_DIR)/$(TARGET).map,--cref \
          -Wl,--gc-sections

# ---------------------------------------------------------------------------
# Default
# ---------------------------------------------------------------------------
all: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin publish

# Copy release artefacts to the firmware-project root publish dir (../BUILD/),
# matching project.yaml::build_out_dir. This is what stm32-build-flash and
# downstream tooling consume.
publish: $(BUILD_DIR)/$(TARGET).elf $(BUILD_DIR)/$(TARGET).hex $(BUILD_DIR)/$(TARGET).bin | $(PUBLISH_DIR)
	cp -f $(BUILD_DIR)/$(TARGET).elf $(PUBLISH_DIR)/
	cp -f $(BUILD_DIR)/$(TARGET).hex $(PUBLISH_DIR)/
	cp -f $(BUILD_DIR)/$(TARGET).bin $(PUBLISH_DIR)/

$(PUBLISH_DIR):
	mkdir -p $@

# ---------------------------------------------------------------------------
# Build rules
# ---------------------------------------------------------------------------
OBJECTS  = $(addprefix $(BUILD_DIR)/, $(notdir $(C_SOURCES:.c=.o)))
vpath %.c $(sort $(dir $(C_SOURCES)))

OBJECTS += $(addprefix $(BUILD_DIR)/, $(notdir $(ASM_SOURCES:.s=.o)))
vpath %.s $(sort $(dir $(ASM_SOURCES)))

$(BUILD_DIR)/%.o: %.c Makefile | $(BUILD_DIR)
	$(CC) -c $(CFLAGS) -Wa,-a,-ad,-alms=$(BUILD_DIR)/$(notdir $(<:.c=.lst)) $< -o $@

$(BUILD_DIR)/%.o: %.s Makefile | $(BUILD_DIR)
	$(AS) -c $(CFLAGS) $< -o $@

$(BUILD_DIR)/$(TARGET).elf: $(OBJECTS) Makefile
	$(CC) $(OBJECTS) $(LDFLAGS) -o $@
	$(SZ) $@

$(BUILD_DIR)/%.hex: $(BUILD_DIR)/%.elf | $(BUILD_DIR)
	$(HEX) $< $@

$(BUILD_DIR)/%.bin: $(BUILD_DIR)/%.elf | $(BUILD_DIR)
	$(BIN) $< $@

$(BUILD_DIR):
	mkdir -p $@

# ---------------------------------------------------------------------------
# Flash via openocd (on-board ST-LINK/V2.1).
# ---------------------------------------------------------------------------
OPENOCD = openocd
OPENOCD_IF = -f interface/stlink.cfg
OPENOCD_TGT = -f target/stm32g0x.cfg

flash: $(BUILD_DIR)/$(TARGET).elf
	$(OPENOCD) $(OPENOCD_IF) $(OPENOCD_TGT) \
	  -c "program $< verify reset exit"

erase:
	$(OPENOCD) $(OPENOCD_IF) $(OPENOCD_TGT) \
	  -c "init; reset halt; stm32g0x mass_erase 0; exit"

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------
clean:
	rm -rf $(BUILD_DIR)

# Dep file inclusion
-include $(wildcard $(BUILD_DIR)/*.d)

.PHONY: all clean flash erase publish
