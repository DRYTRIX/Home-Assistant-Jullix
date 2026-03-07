"""Constants for the Jullix integration."""

DOMAIN = "jullix"

# Platform API
API_BASE_URL = "https://mijn.jullix.be"
API_PATH_INSTALLATIONS = "/api/v1/installation/all"
API_PATH_INSTALLATION = "/api/v1/installation/{install_id}"
API_PATH_POWER_SUMMARY = "/api/v1/actual/{install_id}/summary/power"
API_PATH_ACTUAL_DETAIL = "/api/v1/actual/{install_id}/detail/{detail_type}"
API_PATH_ACTUAL_METERING = "/api/v1/actual/{install_id}/detail/metering"
API_PATH_CHARGERS = "/api/v1/charger/installation/{install_id}/all"
API_PATH_CHARGER_STATUS = "/api/v1/charger/{mac}/status"
API_PATH_CHARGER_CONTROL = "/api/v1/charger/{mac}/control"
API_PATH_PLUGS = "/api/v1/plug/installation/{install_id}/all"
API_PATH_PLUG_CONTROL = "/api/v1/plug/{mac}/control"
API_PATH_COST_SAVINGS = "/api/v1/cost/savings/{install_id}"
API_PATH_COST_TOTAL = "/api/v1/cost/total/{install_id}/{year}/{month}"
API_PATH_ALGORITHM_SETTINGS = "/api/v1/algorithm/settings/{install_id}"
API_PATH_ALGORITHM_FORCE = "/api/v1/algorithm/force/command/{install_id}"

# API returns power in kW; we convert to W for Home Assistant compatibility
API_POWER_IN_KW = True

# Jullix-Direct (local)
LOCAL_EMS_ENDPOINTS = ["meter", "solar", "battery", "charger", "plug"]
LOCAL_DEFAULT_HOST = "jullix.local"

# Config
DEFAULT_SCAN_INTERVAL = 60  # seconds
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 300

# Config flow
CONF_API_TOKEN = "api_token"
CONF_INSTALL_IDS = "install_ids"
CONF_LOCAL_HOST = "local_host"

# Options (keys stored in config_entry.options)
OPTION_SCAN_INTERVAL = "update_interval"
OPTION_ENABLE_COST = "enable_cost"
OPTION_ENABLE_CHARGER_CONTROL = "enable_charger_control"
OPTION_ENABLE_PLUG_CONTROL = "enable_plug_control"
OPTION_USE_LOCAL = "use_local"
OPTION_DEFAULT_INSTALL = "default_install"

# Alias for coordinator/__init__
CONF_UPDATE_INTERVAL = OPTION_SCAN_INTERVAL
DEFAULT_UPDATE_INTERVAL = DEFAULT_SCAN_INTERVAL
