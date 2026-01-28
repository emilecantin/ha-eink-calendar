# Example Configuration Files

This directory contains example configuration files for the test environment.

## Usage

After starting the test environment for the first time:

```bash
# Copy example config
cp ha-test-config.example/configuration.yaml ha-test-config/configuration.yaml

# Restart to apply
./test-env.sh restart
```

## What's Included

- **configuration.yaml** - Basic HA config with EPCAL debug logging enabled

## Customization

Edit `ha-test-config/configuration.yaml` to:

- Change timezone
- Enable demo calendars
- Adjust log levels
- Add other integrations

After changes, restart: `./test-env.sh restart`
