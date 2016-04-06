"""
Support for Homematic (HM-TC-IT-WM-W-EU, HM-CC-RT-DN) thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/thermostat.homematic/
"""
import logging
import socket
import time
import threading
from xmlrpc.client import ServerProxy

from homeassistant.components.thermostat import ThermostatDevice
from homeassistant.const import TEMP_CELCIUS
from homeassistant.helpers.temperature import convert

REQUIREMENTS = []

CONF_ADDRESS = 'address'
CONF_DEVICES = 'devices'
CONF_ID = 'id'
PROPERTY_SET_TEMPERATURE = 'SET_TEMPERATURE'
PROPERTY_VALVE_STATE = 'VALVE_STATE'
PROPERTY_ACTUAL_TEMPERATURE = 'ACTUAL_TEMPERATURE'
PROPERTY_BATTERY_STATE = 'BATTERY_STATE'
PROPERTY_CONTROL_MODE = 'CONTROL_MODE'
PROPERTY_BURST_MODE = 'BURST_RX'

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Homematic thermostat."""
    devices = []
    try:
        lock = threading.Lock()
        for name, device_cfg in config[CONF_DEVICES].items():
            homegear = ServerProxy(config[CONF_ADDRESS])
            # get device description to detect the type
            device_type = homegear.getDeviceDescription(
                device_cfg[CONF_ID] + ':-1')['TYPE']

            if device_type in ['HM-CC-RT-DN', 'HM-CC-RT-DN-BoM']:
                devices.append(HomematicThermostat(homegear,
                                                   device_cfg[CONF_ID],
                                                   name, 4, lock))
            elif device_type in ['BC-RT-TRX-CyG', 'BC-RT-TRX-CyG-2']:
                devices.append(HomematicThermostat(homegear,
                                                   device_cfg[CONF_ID],
                                                   name, 1, lock))
            elif device_type == 'HM-TC-IT-WM-W-EU':
                devices.append(HomematicThermostat(homegear,
                                                   device_cfg[CONF_ID],
                                                   name, 2, lock))
            else:
                raise ValueError(
                    "Device Type '{}' currently not supported".format(
                        device_type))
    except socket.error:
        _LOGGER.exception("Connection error to homematic web service")
        return False

    add_devices(devices)

    return True


# pylint: disable=too-many-instance-attributes
class HomematicThermostat(ThermostatDevice):
    """Representation of a Homematic thermostat."""

    def __init__(self, device, _id, name, channel, lock):
        """Initialize the thermostat."""
        self.device = device
        self._id = _id
        self._channel = channel
        self._name = name
        self._full_device_name = '{}:{}'.format(self._id, self._channel)

        self._current_temperature = None
        self._target_temperature = None
        self._valve = None
        self._battery = None
        self._mode = None
        self._lock = lock
        self.update()

    @property
    def should_poll(self):
        """Yes, please, Homematic has to be polled."""
        return True
                        

    @property
    def name(self):
        """Return the name of the Homematic device."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement that is used."""
        return TEMP_CELCIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def _acquire_lock(self):
        self._lock.acquire(True, 5)
    
    def _release_lock(self):
        self._lock.release()

    def set_temperature(self, temperature):
        """Set new target temperature."""
        self.device.setValue(self._full_device_name,
                             PROPERTY_SET_TEMPERATURE,
                             temperature)

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {"valve": self._valve,
                "battery": self._battery,
                "mode": self._mode}


    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return round(convert(4.5, TEMP_CELCIUS, self.unit_of_measurement))
                        
    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return round(convert(30.5, TEMP_CELCIUS, self.unit_of_measurement))


    def update(self):
        """Update the data from the thermostat."""
        
#        _LOGGER.info("HOMEMATIC UPDATE!")
        
        try:
            self._current_temperature = self.device.getValue(
                self._full_device_name,
                PROPERTY_ACTUAL_TEMPERATURE)
            self._target_temperature = self.device.getValue(
                self._full_device_name,
                PROPERTY_SET_TEMPERATURE)

#            _LOGGER.info("Found temp: " + str(self._target_temperature))

            self._valve = self.device.getValue(self._full_device_name,
                                               PROPERTY_VALVE_STATE)
            if (self._channel!=1):
                self._battery = self.device.getValue(self._full_device_name,
                                                     PROPERTY_BATTERY_STATE)

            self._mode = self.device.getValue(self._full_device_name,
                                              PROPERTY_CONTROL_MODE)
        except:
            _LOGGER.exception("Did not receive any temperature data from the "
                              "homematic API.")
        
                      