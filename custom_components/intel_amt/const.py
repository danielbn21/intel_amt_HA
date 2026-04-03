"""Constants for the Intel AMT integration."""

DOMAIN = "intel_amt"
MANUFACTURER = "Intel"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TLS = "tls"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 16992
DEFAULT_PORT_TLS = 16993
DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_TLS = False

# Entity unique ID suffixes
ENTITY_POWER_STATE = "power_state"
ENTITY_POWER_STATE_CODE = "power_state_code"
ENTITY_IS_ON = "is_on"

# Services
SERVICE_POWER_ON = "power_on"
SERVICE_POWER_OFF = "power_off"
SERVICE_SOFT_POWER_OFF = "soft_power_off"
SERVICE_RESET = "reset"
SERVICE_SOFT_RESET = "soft_reset"
SERVICE_POWER_CYCLE = "power_cycle"
SERVICE_HIBERNATE = "hibernate"
SERVICE_NMI = "nmi"

# Platforms
PLATFORMS = ["sensor", "binary_sensor", "button", "switch"]
