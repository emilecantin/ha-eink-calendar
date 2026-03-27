PIO_DIR = Arduino/epcal
COMPONENT_DIR = custom_components/eink_calendar
FIRMWARE_BIN = $(PIO_DIR)/.pio/build/esp32dev/firmware.bin
FW_VERSION = $(shell cat $(PIO_DIR)/firmware.version)

# Pass firmware version to PlatformIO as a build flag
export PLATFORMIO_BUILD_FLAGS = -DFIRMWARE_VERSION='"$(FW_VERSION)"'

# --- Firmware ---

build:
	@echo "Building firmware v$(FW_VERSION)..."
	pio run -d $(PIO_DIR)

bundle: build  ## Build firmware and copy .bin + version into the HA integration
	cp $(FIRMWARE_BIN) $(COMPONENT_DIR)/firmware.bin
	cp $(PIO_DIR)/firmware.version $(COMPONENT_DIR)/firmware.version
	@echo "Bundled firmware v$(FW_VERSION) into $(COMPONENT_DIR)/"

upload:
	pio run -d $(PIO_DIR) -t upload

erase:
	pio run -d $(PIO_DIR) -t erase

monitor:
	pio device monitor -d $(PIO_DIR) -b 115200

flash: upload monitor  ## upload + open serial monitor

# --- Tests ---

test:
	custom_components/eink_calendar/tests/run_tests.sh --no-header -q

test-verbose:
	custom_components/eink_calendar/tests/run_tests.sh -v

# --- Home Assistant ---

ha:
	docker-compose up

# --- Helpers ---

help:
	@echo "Firmware:"
	@echo "  make build       Build ESP32 firmware"
	@echo "  make bundle      Build + copy .bin into HA integration"
	@echo "  make upload      Build and upload via USB"
	@echo "  make erase       Erase flash"
	@echo "  make monitor     Open serial monitor"
	@echo "  make flash       Upload + monitor"
	@echo ""
	@echo "Tests:"
	@echo "  make test        Run Python tests (quiet)"
	@echo "  make test-verbose  Run with verbose output"
	@echo ""
	@echo "Home Assistant:"
	@echo "  make ha          Start HA dev environment"

.PHONY: build bundle upload erase monitor flash test test-verbose ha help
.DEFAULT_GOAL := help
