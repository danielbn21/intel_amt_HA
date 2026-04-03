# Intel AMT – Home Assistant Custom Integration

Control and monitor machines with Intel Active Management Technology (AMT / vPro) directly from Home Assistant.

## Features

- **Binary Sensor** – `Power` – on/off based on AMT power state
- **Sensor** – `Power State` – human-readable state (On, Off, Hibernate, Sleep…)
- **Sensor** – `Power State Code` – raw CIM code (hidden by default, useful for automations)
- **Switch** – `Power Switch` – toggle power on/off (hard power on / hard power off)
- **Buttons** (one per action):
  - Power On
  - Power Off (Hard) – immediate cut
  - Shutdown (Graceful) – soft OS shutdown *(requires Intel LMS running in OS)*
  - Reset (Hard) – immediate hard reset
  - Reboot (Graceful) – soft OS reboot *(requires Intel LMS running in OS)*
  - Power Cycle – soft power cycle
  - Hibernate
  - Send NMI – non-maskable interrupt (diagnostic)

All communication is done via WS-Management (SOAP/HTTP) directly to the AMT device — no extra software required on the managed machine.

---

## Requirements

- Intel vPro / AMT enabled machine (AMT 7.0+)
- AMT configured and network access enabled (in MEBx or via MeshCommander)
- Home Assistant 2023.1 or newer
- `aiohttp` (included by default in HA)

---

## Installation

### Manual (recommended while testing)

1. Copy the `intel_amt` folder into your HA `config/custom_components/` directory:
   ```
   config/
   └── custom_components/
       └── intel_amt/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           ├── const.py
           ├── amt_client.py
           ├── entity.py
           ├── sensor.py
           ├── binary_sensor.py
           ├── switch.py
           ├── button.py
           ├── strings.json
           └── translations/
               └── en.json
   ```
2. Restart Home Assistant.

### HACS (recommended once published)

1. In Home Assistant go to **HACS → Integrations → ⋮ → Custom repositories**
2. Add your GitHub repo URL, category = **Integration**
3. Find **Intel AMT** in HACS and click **Download**
4. Restart Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=YOUR_GITHUB_USER&repository=intel_amt&category=integration)

---

## Examples

The `examples/` folder contains ready-to-use YAML for:

| File | Contents |
|------|----------|
| `examples/automations.yaml` | 7 automations — scheduled power-on/off, mobile alerts, power-cycle watchdog |
| `examples/scripts.yaml` | 4 reusable scripts — safe reboot/shutdown with fallback, NMI helper |
| `examples/lovelace_cards.yaml` | 4 dashboard cards — full control panel, minimal list, Mushroom chips, history graph |

See `examples/lovelace_cards.yaml` for the full control panel card (recommended starting point).

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Intel AMT**
3. Fill in:
   - **Host / IP**: IP address of the AMT machine (e.g. `192.168.1.50`)
   - **Username**: `admin` (default AMT username)
   - **Password**: Your AMT password set in MEBx
   - **Port**: `16992` for HTTP, `16993` for TLS
   - **Use TLS**: Enable if your AMT is configured for HTTPS
   - **Poll Interval**: How often to check status (default 30 seconds)

---

## AMT Setup (MEBx)

If not already configured, on the target machine:

1. Boot and press **Ctrl+P** to enter MEBx
2. Login with default password `admin`, set a new password
3. Under **Intel AMT Configuration**:
   - Enable **Network Access**
   - Set static IP or note the DHCP IP
   - Under **User Consent** → set to **None** for unattended operation
4. Activate

You can also use **MeshCommander** firmware flashed to AMT to manage this via browser at `http://<AMT-IP>:16992`.

---

## Power State Reference

| Code | State | Notes |
|------|-------|-------|
| 2 | On | Machine is running |
| 6 | Off (Hard) | Machine is fully off |
| 7 | Hibernate | |
| 8 | Off (Soft) | |
| 3 | Sleep Light | |
| 4 | Sleep Deep | |

---

## Notes on Graceful Actions

The **Shutdown (Graceful)** and **Reboot (Graceful)** buttons send AMT power codes 12 and 14 respectively. These require:
- The OS to be running
- Intel Local Manageability Service (LMS/IMSS) installed in the OS

Hard power actions (Power On, Power Off Hard, Reset Hard) work even when the OS is completely off.

---

## Troubleshooting

- **Cannot connect**: Check that AMT is activated, the IP/port is correct, and no firewall blocks port 16992
- **Invalid auth**: Double-check the AMT password in MEBx settings
- **Power state shows Unknown**: The SOAP response may vary by AMT firmware version; check HA logs for raw XML
- **TLS errors**: If using TLS, AMT uses a self-signed certificate — the integration bypasses SSL verification automatically

---

## License

Apache 2.0
