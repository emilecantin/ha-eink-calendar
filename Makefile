PIO_DIR = Arduino/epcal
COMPONENT_DIR = custom_components/eink_calendar
TEST_DIR = $(COMPONENT_DIR)/tests
FIRMWARE_BIN = $(PIO_DIR)/.pio/build/esp32dev/firmware.bin
FW_VERSION = $(shell cat $(PIO_DIR)/firmware.version)
VENV = .venv
PYTEST = $(VENV)/bin/python -m pytest

# Pass firmware version to PlatformIO as a build flag
export PLATFORMIO_BUILD_FLAGS = -DFIRMWARE_VERSION='"$(FW_VERSION)"'

# --- Firmware ---

build:
	@echo "Building firmware v$(FW_VERSION)..."
	pio run -d $(PIO_DIR)

bundle: build
	cp $(FIRMWARE_BIN) $(COMPONENT_DIR)/firmware.bin
	cp $(PIO_DIR)/firmware.version $(COMPONENT_DIR)/firmware.version
	@echo "Bundled firmware v$(FW_VERSION) into $(COMPONENT_DIR)/"

upload:
	pio run -d $(PIO_DIR) -t upload

erase:
	pio run -d $(PIO_DIR) -t erase

monitor:
	pio device monitor -d $(PIO_DIR) -b 115200

flash: upload monitor

# --- Dependencies ---

$(VENV)/bin/activate: requirements-test.txt
	test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r requirements-test.txt
	@touch $@

# --- Tests ---

test: test-unit test-esp test-integration

test-unit: $(VENV)/bin/activate
	cd $(TEST_DIR) && ../../../$(PYTEST) --no-header -q --ignore=integration $(ARGS)

test-esp:
	pio test -d $(PIO_DIR) -e native

test-integration: $(VENV)/bin/activate ha-test-up
	@echo "Provisioning HA test instance..."
	@HA_TOKEN=$$(HA_URL=http://localhost:18123 $(VENV)/bin/python $(TEST_DIR)/integration/provision_ha.py) || \
		{ echo "ERROR: HA provisioning failed"; exit 1; }; \
	cd $(TEST_DIR)/integration && HA_URL=http://localhost:18123 HA_TOKEN=$$HA_TOKEN ../../../../$(PYTEST) --rootdir=. -v --tb=short $(ARGS)

ha-test-up:
	@docker compose -f docker-compose.test.yml up -d
	@echo "Waiting for Home Assistant..."
	@timeout=120; elapsed=0; \
	until curl -sf http://localhost:18123/api/onboarding > /dev/null 2>&1; do \
		[ $$elapsed -ge $$timeout ] && echo "ERROR: HA did not start within $${timeout}s" && exit 1; \
		sleep 2; elapsed=$$((elapsed + 2)); printf "."; \
	done; echo ""
	@echo "Home Assistant ready at http://localhost:18123"

ha-test-down:
	docker compose -f docker-compose.test.yml down

ha-test-clean: ha-test-down
	rm -rf ha-test-config/.storage ha-test-config/.HA_VERSION
	@echo "Test HA storage cleared. Next 'make ha-test-up' will trigger fresh onboarding."

# --- Home Assistant (dev) ---

ha:
	docker-compose up

# --- Helpers ---

help:
	@echo "Firmware:"
	@echo "  make build            Build ESP32 firmware"
	@echo "  make bundle           Build + copy .bin into HA integration"
	@echo "  make upload           Build and upload via USB"
	@echo "  make erase            Erase flash"
	@echo "  make monitor          Open serial monitor"
	@echo "  make flash            Upload + monitor"
	@echo ""
	@echo "Tests:"
	@echo "  make test             Run ALL tests (unit + ESP + integration)"
	@echo "  make test-unit        Run Python unit tests"
	@echo "  make test-esp         Run ESP32 native tests (PlatformIO)"
	@echo "  make test-integration Run integration tests against HA in Docker"
	@echo "  make test-unit ARGS='-k weather'   Pass extra pytest args"
	@echo ""
	@echo "Home Assistant:"
	@echo "  make ha               Start HA dev environment"
	@echo "  make ha-test-up       Start HA test instance (port 18123)"
	@echo "  make ha-test-down     Stop HA test instance"
	@echo "  make ha-test-clean    Stop + wipe HA test data (forces re-onboarding)"

.PHONY: build bundle upload erase monitor flash \
        test test-unit test-esp test-integration \
        ha ha-test-up ha-test-down ha-test-clean help
.DEFAULT_GOAL := help
