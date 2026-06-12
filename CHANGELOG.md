# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2026-06-12

### Added
- Timer sensor (`sensor.alfeedo_timers`) exposing the list of active timers as attributes, including timer id, time (HH:MM), mode, and maximum number of timers allowed
- Timer UI in the custom card: view, add, and delete timers directly from the dashboard
- HA services `alfeedo.add_timer` (time, mode) and `alfeedo.delete_timer` (timer_id) to manage timers from automations or scripts
- Diagnostic sensors: WiFi RSSI, WiFi SSID, IP address, uptime, free heap memory, firmware version
- Motor settings as number sliders: meal size (revolutions), snack size (revolutions), motor speed — with dynamic min/max values read from the ESP32 API
- Fill sensor settings as number sliders: full measurement (mm), empty measurement (mm)
- Restart button (`button.alfeedo_restart_feeder`) to reboot the ESP32 remotely

### Changed
- `async_get_data()` now fetches status, motor settings, fill sensor settings, and timers in parallel on every poll
- Lovelace resource URL now includes the version number from `manifest.json` (e.g. `ha-alfeedo.js?v=0.1.3`) to automatically bust the browser cache on updates
- Old Lovelace resource entries with a different version are automatically removed and replaced on HA startup
- `cache_headers` set to `False` on the static path to prevent stale JS being served after updates

### Fixed
- Custom card not appearing in the card picker due to `async_setup` not being called when the integration was added via the UI only (workaround: add `alfeedo:` to `configuration.yaml`, or use the Lovelace resource URL with version parameter)
- Browser cache causing old card version to be loaded after updates — resolved by versioned resource URL and removal of cached `.gz` file
