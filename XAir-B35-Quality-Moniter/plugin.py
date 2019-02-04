# coding=UTF-8
# XAir B35 Quality Moniter Python Plugin
#
# Author: xiaoyao9184
#
"""
<plugin 
    key="XAir-B35-Quality-Moniter"
    name="XAir B35 Quality Moniter"
    author="xiaoyao9184"
    version="0.1"
    externallink="https://github.com/xiaoyao9184/Domoticz-XAir-Plugin">
    <params>
        <param field="Mode1" label="Debug" width="200px">
            <options>
                <option label="None" value="none" default="none"/>
                <option label="Debug(Only Domoticz)" value="debug"/>
                <option label="Debug(Attach by ptvsd)" value="ptvsd"/>
                <option label="Debug(Attach by rpdb)" value="rpdb"/>
            </options>
        </param>
        <param field="Mode2" label="Repeat Time(s)" width="30px" required="true" default="60"/>
        <param field="Mode3" label="USB" width="100px" default="COM5"/>
        </params>
</plugin>
"""

# Fix import of libs installed with pip as PluginSystem has a wierd pythonpath...
import os
import sys
import site
for mp in site.getsitepackages():
    sys.path.append(mp)

import Domoticz
import time


class Heartbeat():

    def __init__(self, interval):
        self.callback = None
        self.count = 0
        # stage interval
        self.seek = 0
        self.interval = 10
        # real interval
        self.total = 10
        if (interval < 0):
            pass
        elif (0 < interval and interval < 30):
            self.interval = interval
            self.total = interval
        else:
            result = self.show_factor(interval, self.filter_factor, self.bast_factor)
            self.seek = result["repeat"]
            self.interval = result["factor"]
            self.total = result["number"]

    def setHeartbeat(self, func_callback):
        Domoticz.Heartbeat(self.interval)
        Domoticz.Log("Heartbeat total interval set to: " + str(self.total) + ".")
        self.callback = func_callback
            
    def beatHeartbeat(self):
        self.count += 1
        if (self.count >= self.seek):
            self.count = 0
            if self.callback is not None:
                Domoticz.Log("Calling heartbeat handler " + str(self.callback.__name__) + ".")
                self.callback()
        else:
            Domoticz.Log("Skip heartbeat handler bacause stage not enough " + str(self.count) + "/" + str(self.seek) + ".")

    def filter_factor(self, factor):
        return factor < 30 and factor > 5

    def show_factor(self, number, func_filter, func_prime):
        factor = number // 2
        while factor > 1:
            if number % factor == 0 and func_filter(factor):
                return {
                    "number": number,
                    "factor": factor,
                    "repeat": int(number / factor)
                }
            factor-=1
        else:
            return func_prime(number)

    def next_factor(self, number):
        return self.show_factor(number + 1, self.filter_factor, self.next_factor)

    def last_factor(self, number):
        return self.show_factor(number - 1, self.filter_factor, self.last_factor)

    def bast_factor(self, number):
        n = self.next_factor(number)
        l = self.last_factor(number)

        if n["factor"] >= l["factor"]:
            return n
        else:
            return l

# 
def MapValue(value):
    return int(value)

# fix pm0.3
def MapTextPM03(value):
    n = int(value) * 10
    return str(n)

# fix humidity
def MapTextHumidity(value):
    sValue = 0
    n = int(value)
    if n < 46:
        sValue = 2        #dry
    elif n > 70:
        sValue = 3        #wet
    else:
        sValue = 1        #comfortable
    return sValue

def UpdateDevice(Unit, nValue, sValue):
    if (Unit not in Devices): return
    Domoticz.Debug("Update '" + Devices[Unit].Name + "' : " + str(nValue) + " - " + str(sValue))
    # Warning: The lastest beta does not completly support python 3.5
    # and for unknown reason crash if Update methode is called whitout explicit parameters
    Devices[Unit].Update(nValue = nValue, sValue = str(sValue))
    return

class XAirB35Plugin:

    __UNIT_PM03 = 1
    __UNIT_PM25 = 2
    __UNIT_HCHO = 3
    __UNIT_CO2 = 4
    __UNIT_TEMPERATURE = 5
    __UNIT_HUMIDITY = 6

    # Can't use 'Gas' Type, Gas is for usage amount
    __UNITS = [
        {
            "_Name": "XAir_PM0.3", 
            "_Unit": __UNIT_PM03, 
            "_TypeName": "Custom",
            "_TypeID": 151,
            "_SubtypeID": 2,
            "_Options": {
                "Custom": "1;count/L"
            }, 
            "_ValueMap": MapValue,
            "_TextMap": MapTextPM03
        },
        {
            "_Name": "XAir_PM2.5", 
            "_Unit": __UNIT_PM25, 
            "_TypeName": "Custom",
            "_TypeID": 151,
            "_SubtypeID": 2,
            "_Options": {
                "Custom": "1;μg/m³"
            }, 
            "_ValueMap": MapValue
        },
        {
            "_Name": "XAir_HCHO", 
            "_Unit": __UNIT_HCHO, 
            "_TypeName": "Custom",
            "_TypeID": 151,
            "_SubtypeID": 2,
            "_Options": {
                "Custom": "1;μg/m³"
            }, 
            "_ValueMap": MapValue
        },
        {
            "_Name": "XAir_CO2", 
            "_Unit": __UNIT_CO2, 
            "_TypeName": "Air Quality",
            "_TypeID": 249,
            "_SubtypeID": 1,
            "_Options": None,
            "_ValueMap": MapValue
        },
        {
            "_Name": "XAir_Temperature", 
            "_Unit": __UNIT_TEMPERATURE, 
            "_TypeName": "Temperature",
            "_TypeID": 80,
            "_SubtypeID": 5,
            "_Options": None,
            "_ValueMap": MapValue,
        },
        {
            "_Name": "XAir_Humidity", 
            "_Unit": __UNIT_HUMIDITY, 
            "_TypeName": "Humidity",
            "_TypeID": 81,
            "_SubtypeID": 1,
            "_Options": None,
            "_ValueMap": MapValue,
            "_TextMap": MapTextHumidity
        }
    ]

    serialConn = None
    lastTime = None

    def onStart(self):
        # Debug
        debug = 0
        if (Parameters["Mode1"] != "none"):
            Domoticz.Debugging(1)
            debug = 1
        
        if (Parameters["Mode1"] == 'ptvsd'):
            Domoticz.Log("Debugger ptvsd started, use 0.0.0.0:5678 to attach")
            import ptvsd
            # signal error on raspberry
            ptvsd.enable_attach()
            ptvsd.wait_for_attach()
        elif (Parameters["Mode1"] == 'rpdb'):
            Domoticz.Log("Debugger rpdb started, use 'telnet 0.0.0.0 4444' to connect")
            import rpdb
            rpdb.set_trace()
            # signal error on raspberry
            # rpdb.handle_trap("0.0.0.0", 4444)

        # Heartbeat
        self.heartbeat = Heartbeat(int(Parameters["Mode2"]))
        self.heartbeat.setHeartbeat(self.AutoConnect)
        
        # Serial Connection
        usb = Parameters["Mode3"]
        self.serialConn = Domoticz.Connection(
            Name="Usb", Transport="Serial", Protocol="Line", 
            Address=usb, Baud=57600)
        self.serialConn.Connect()

        self.CreateDevice()
        return

    def onStop(self):
        Domoticz.Log("onStop called")
        self.serialConn.Disconnect()
        return

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")
        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address)
            Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Connection.Address+" with error: "+Description)
        return

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")
        self.serialConn.Connect()
        return

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("onNotification called: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)
        return

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called: Connection=" + str(Connection) + ", Data=" + str(Data))
        self.UpdateDevice(Data)
        return
        
    def onHeartbeat(self):
        self.heartbeat.beatHeartbeat()
        return

    def CreateDevice(self):
        # Create devices
        for unit in self.__UNITS:
            if unit["_Unit"] not in Devices:
                Domoticz.Device(
                    Name = unit["_Name"], 
                    Unit = unit["_Unit"],
                    TypeName = unit["_TypeName"],
                    # Type = unit["_TypeID"], 
                    # Subtype = unit["_SubtypeID"],
                    Options = unit["_Options"], 
                ).Create()
        return

    def UpdateDevice(self,Data):
        self.lastTime = int(time.time())
        if len(Data) > 0:
            strData = Data.decode("utf-8", "ignore").replace('\r\n','')
            datas = strData.split(',')
            Domoticz.Debug('Receive number: ' + datas[6] + " data:" + strData)
            for unit, data in zip(self.__UNITS, datas):
                n = 1
                s = data
                if "_ValueMap" in unit.keys():
                    n = unit["_ValueMap"](data)
                if "_TextMap" in unit.keys():
                    s = unit["_TextMap"](data)
                UpdateDevice(unit["_Unit"], n, s)      
        return

    def AutoConnect(self):
        if not self.serialConn.Connected():
            Domoticz.Debug("Serial not connected, try connect it.")
            self.serialConn.Connect()
            return

        seconds = (int(time.time()) - self.lastTime)
        if self.lastTime != 0 and seconds > 60:
            Domoticz.Debug("Serial not receive in " + str(seconds) + " seconds, try reconnect it.")
            self.serialConn.Disconnect()
            self.serialConn.Connect()
            return

        Domoticz.Debug("Serial receive in " + str(seconds) + " seconds ago, do nothing.")
        return

global _plugin
_plugin = XAirB35Plugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

