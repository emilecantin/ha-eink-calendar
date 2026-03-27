PIO_DIR = Arduino/epcal

# --- Firmware ---

build:
	pio run -d $(PIO_DIR)

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

.PHONY: build upload erase monitor flash test test-verbose ha help
.DEFAULT_GOAL := help
