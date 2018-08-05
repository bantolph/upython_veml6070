"""
Micropython VEML6070 library from VISHAY SEMICONDUCTORS
UV LIGHT SENSOR WITH I2C INTERFACE
Datasheet: http://www.vishay.com/docs/84310/designingveml6070.pdf
Code shamelessly lifted, adapted and uglied up from:
    Adafruit  `adafruit_veml6070` - VEML6070 UV Sensor
    https://github.com/adafruit/Adafruit_CircuitPython_VEML6070.git

    Christian Nicolai's Python VEML6070 module
    https://github.com/cmur2/python-veml6070
"""
from micropython import const
import utime

VEML6070_ADDR_ARA  = const(0x18 >> 1)
VEML6070_ADDR_CMD  = const(0x70 >> 1)
VEML6070_ADDR_LOW  = const(0x71 >> 1)
VEML6070_ADDR_HIGH = const(0x73 >> 1)
VEML6070_INTEGRATION_TIME = { "VEML6070_HALF_T": [0x00, 0],
                              "VEML6070_1_T": [0x01, 1],
                              "VEML6070_2_T": [0x02, 2],
                              "VEML6070_4_T": [0x03, 4]
                            }

class VEML6070(object):
    """
    Class to read from a Vishay VEML6070 UV module
    - sample code

    from machine import Pin
    from machine import I2C
    sda = Pin(4)
    scl = Pin(5)
    i2c = I2C(sda=sda, scl=scl)
    i2c.scan()
    from veml6070 import VEML6070
    veml = VEML6070(i2c)
    veml.read()
    veml.uvi()
    """
    def __init__(self, i2c, ack=False):
        # i2c is a I2C class from the machine module in upython
        self.i2c = i2c
        self.ara_buf = bytearray(1)
        self.buf = bytearray(1)
        self.ack=ack
        self.ack_thd = 0x00
        self.integration_time = 'VEML6070_1_T'
        self.rset = 'RSET_270K'

        # Initialize
        i2c.writeto_mem(VEML6070_ADDR_LOW, VEML6070_ADDR_ARA, self.ara_buf)
        self.buf[0]=ack << 5 |VEML6070_INTEGRATION_TIME['VEML6070_1_T'][0] <<2
        i2c.writeto(VEML6070_ADDR_CMD, self.buf)

    def set_integration_time(self, it):
        # make sure the IT is in the dictionary for valid IT times
        if it not in VEML6070_INTEGRATION_TIME:
            return False
        self.integration_time = it
        self.buf[0]=ack << 5 |VEML6070_INTEGRATION_TIME[self.integration_time][0] <<2
        self.i2c.writeto(VEML6070_ADDR_CMD, self.buf)
        return True

    def get_refresh_time(self):
        # return enough time for the veml module to get a good reading
        case_refresh_rset = {'RSET_240K': 0.1,
                             'RSET_270K': 0.1125,
                             'RSET_300K': 0.125,
                             'RSET_600K': 0.25
                            }

        return case_refresh_rset[self.rset] *  VEML6070_INTEGRATION_TIME[self.integration_time][1]


    def read(self):
        # read a value and return the raw vaule
        # wake up module
        self.wake()
        # wait long enough for the veml module to get a good reading
        utime.sleep(self.get_refresh_time())
        read_buf = bytearray(2)
        lsb = bytearray(1)
        msb = bytearray(1)
        self.i2c.readfrom_into(VEML6070_ADDR_LOW, lsb, 1)
        self.i2c.readfrom_into(VEML6070_ADDR_HIGH, msb, 1)
        read_buf = msb + lsb
        raw = read_buf[1] << 8 | read_buf[0]
        # put the module back in low power mode
        self.shutdown()
        return raw

    def uva_light_sensitivity(self):
        """
        Return the UV light senstivity
        """
        raw = self.read()
        # RSET_270K = 270000, RSET_270K: 0.05625
        return raw * (0.05625 / VEML6070_INTEGRATION_TIME[self.integration_time][1])

    def uv_risk(self):
        """
        Return risk level
        """
        raw = self.read()
        # for now only the resistor setting a 270k is supported
        VEML6070_RISK_LEVEL = { 'RSET_270K': {"LOW": [0, 560],
                                       "MODERATE": [561, 1120],
                                       "HIGH": [1121, 1494],
                                       "VERY HIGH": [1495, 2054],
                                       "EXTREME": [2055, 9999]
                                      }
                       }
        # # get the divisor for the current integration time
        div = VEML6070_INTEGRATION_TIME[self.integration_time][1]
        if div == 0:
            raise ValueError( "[veml6070].get_index only available for Integration Times 1, 2, & 4.",
                              "Use [veml6070].set_integration_time(new_it) to change the Integration Time."
                            )
        # adjust the raw value using the divisor, then loop through the Risk Level dict
        # to find which range the adjusted raw value is in.
        raw_adj = int(raw / div)
        for levels in VEML6070_RISK_LEVEL[self.rset]:
            tmp_range = range(VEML6070_RISK_LEVEL[self.rset][levels][0], VEML6070_RISK_LEVEL[self.rset][levels][1])
            if raw_adj in tmp_range:
                risk = levels
                break

        return risk


    def shutdown(self):
        """
        Puts the VEML6070 into shutdown mode
        """
        self.buf[0] = 0x03
        try:
           self.i2c.writeto(VEML6070_ADDR_CMD, self.buf)
        except:
            return False
        return True

    def wake(self):
        """
        Wake the VEML6070 from shutdown mode
        """
        self.buf[0] = (self.ack << 5 | self.ack_thd << 4 | VEML6070_INTEGRATION_TIME[self.integration_time][0] << 2 | 0x02)
        self.i2c.writeto(VEML6070_ADDR_CMD, self.buf)

