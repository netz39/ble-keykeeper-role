#!/usr/bin/python3
import re
import aioserial
import asyncio
import serial.serialutil
import os
from enum import IntEnum
from collections import namedtuple
import argparse
import logging
from ble_helpers import KeykeeperDB


def confirm_authentication():
    '''
    This function is called when a coin successfully authenticated its user.
    '''
    logging.info("opening door")
    os.system("{{door_open_command}}")



class StatusType(IntEnum):
    IDENTITY = 0
    DEVICE_FOUND = 1
    BATTERY_LEVEL = 2
    CONNECTED = 3
    AUTHENTICATED = 4
    DISCONNECTED = 5

class Coin:
    def __init__(self):
        self.battery_level = 0
        self.address = "00:00:00:00:00:00"

class KeykeeperSerialMgr:
    def __init__(self, db):
        self.config_mode = True
        self.db = db
        self.current_coin = Coin()

    # read line and remove color codes
    async def _serial_fetch_line(self):
        line = (await self.central_serial.readline_async()).decode(errors='ignore')
        plain_line = re.sub(r'''
            \x1B    # ESC
            [@-_]   # 7-bit C1 Fe
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        ''', '', line, flags=re.VERBOSE)
        logging.debug(f"received: {plain_line}")
        return plain_line

    # parse status messages
    def _parse_status(self, l):
        regs = {
            StatusType.IDENTITY: r"<inf> bt_hci_core: Identity: (.{17}) \((.*)\)",
            StatusType.DEVICE_FOUND: r"<inf> app: Device found: \[(.{17})\] \(RSSI (-?\d+)\) \(TYPE (\d)\) \(BONDED (\d)\)",
            StatusType.BATTERY_LEVEL: r"<inf> app: Battery Level: (\d{1,3})%",
            StatusType.CONNECTED: r"<inf> app: Connected: \[(.{17})\]",
            StatusType.AUTHENTICATED: r"<inf> app: KEY AUTHENTICATED. OPEN DOOR PLEASE.",
            StatusType.DISCONNECTED: r"<inf> app: Disconnected: \[(.{17})\] \(reason (\d+)\)",
        }
        for k in regs:
            m = re.search(pattern=regs[k], string=l)
            if m:
                return k, m.groups()
        return None, None

    # read registered bonds
    async def _request_bonds(self):
        bonds = []
        self.central_serial.write(b'stats bonds\r\n')
        line = None
        while not (line and line.endswith('stats bonds\r\n')):
            line = await self._serial_fetch_line()
        while line != 'done\r\n':
            line = await self._serial_fetch_line()
            bond = re.match(r"\[(.{17})\] keys: 34, flags: 17\r\n", line)
            if bond:
                bonds.append(bond.groups())
        return bonds

    # read registered spacekeys (only first byte)
    async def _request_spacekeys(self):
        spacekeys = []
        self.central_serial.write(b'stats spacekey\r\n')
        line = None
        while not (line and line.endswith('stats spacekey\r\n')):
            line = await self._serial_fetch_line()
        while line != 'done\r\n':
            line = await self._serial_fetch_line()
            spacekey = re.match(r"\[(.{17})\] : ([A-F0-9]{2})\.\.\.\r\n", line)
            if spacekey:
                spacekeys.append(spacekey.groups())
        return spacekeys

    # read settings
    async def _read_settings(self):
        self.central_serial.write(b'settings load\r\n')
        line = None
        k = None
        while k != StatusType.IDENTITY:
            line = await self._serial_fetch_line()
            k, v = self._parse_status(line)
            if 'bt_hci_core: Read Static Addresses command not available' in line:
                break
            if k == StatusType.IDENTITY:
                self.identity = v[0].upper()

    async def _wait_until_done(self):
        line = None
        while line != 'done\r\n':
            line = await self._serial_fetch_line()

    async def _manage_serial(self):
        # main state machine routine
        # clear old state
        self.identity = None
        self.bonds = None
        self.spacekeys = None

        if self.config_mode:
            logging.info("status: synchronizing database")
            # just load settings, don't start scanning
            await self._read_settings()
            # read coin data from device
            self.bonds = await self._request_bonds()
            self.spacekeys = await self._request_spacekeys()
            if self.identity != self.db.identity[0]:
                if self.identity:
                    self.central_serial.write(b'settings clear\r\n')
                    logging.error(
                        "wrong central identity -> clearing settings")
                    await self._wait_until_done()
                else:
                    self.central_serial.write('central_setup {} {}\r\n'
                                              .format(*self.db.identity)
                                              .encode('ASCII'))
                    await self._wait_until_done()
            if len(self.bonds) != len(self.spacekeys):
                self.central_serial.write(b'settings clear\r\n')
                logging.error("settings corrupted (1) -> clearing settings")
            is_present = {c: False for c in self.db.coins.keys()}
            for bond, skey in zip(self.bonds, self.spacekeys):
                if bond[0] != skey[0]:
                    self.central_serial.write(b'settings clear\r\n')
                    logging.error(
                        "settings corrupted (2) -> clearing settings")
                    await self._wait_until_done()
                if bond[0] not in self.db.coins \
                        or skey[1] != self.db.coins[bond[0]][2][:2]:
                    self.central_serial.write(
                        'coin del {}\r\n'.format(bond[0]).encode('ASCII'))
                    logging.warning(f"deleting {bond[0]}")
                    await self._wait_until_done()
                else:
                    is_present[bond[0]] = True
            for addr, present in is_present.items():
                if not present:
                    self.central_serial.write('coin add {} {} {} {}\r\n'
                                              .format(addr, *self.db.coins[addr])
                                              .encode('ASCII'))
                    logging.warning(f"adding {addr}")
                    await self._wait_until_done()
            self.config_mode = False
            self.central_serial.write(b'reboot\r\n')
            await self._wait_until_done()
        else:
            # start BLE stack
            self.central_serial.write(b'ble_start\r\n')
            logging.info("central connected and scanning")

        # main event loop
        while True:
            line = await self._serial_fetch_line()
            # print(line, end='', flush=True)
            k, v = self._parse_status(line)
            if k == StatusType.IDENTITY:
                self.identity = v[0].upper()
            if k == StatusType.AUTHENTICATED:
                if self.current_coin.address in self.db.names:
                    logging.info("{}'s coin ({}%🔋) authenticated"
                                 .format(self.db.names[self.current_coin.address],
                                         self.current_coin.battery_level))
                else:
                    logging.info("{} ({}%🔋) authenticated"
                                 .format(self.current_coin.address,
                                         self.current_coin.battery_level))
                if not args.test:
                    confirm_authentication()
            elif k == StatusType.BATTERY_LEVEL:
                self.current_coin.battery_level = v[0]
            elif k == StatusType.CONNECTED:
                self.current_coin.address = v[0].upper()
            elif k == StatusType.DISCONNECTED:
                self.current_coin = Coin()

    async def reconnect_loop(self):
        self.current_coin = Coin()

        first_start = True
        while True:
            try:
                self.central_serial = aioserial.AioSerial(
                    port=os.path.realpath(
                        '/dev/serial/by-id/usb-ZEPHYR_N39_BLE_KEYKEEPER_0.01-if00'))
                self.central_serial.write(b'\r\n\r\n')
                if first_start:
                    self.central_serial.write(b'reboot\r\n')
                    first_start = False
                    await self._wait_until_done()

                else:
                    await self._manage_serial()
            except serial.serialutil.SerialException:
                logging.info("connecting to central")
                await asyncio.sleep(1)

    def run(self):
        asyncio.run(self.reconnect_loop())


def run_serialmgr():
    db = KeykeeperDB()
    k = KeykeeperSerialMgr(db)
    k.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='BLE Space Authentication Service script.')
    parser.add_argument('--verbose', action='store_true',
                        default=False, help='print more output')
    parser.add_argument('--test', action='store_true', default=False,
                        help='Do not run door_open_command on successfull auth.')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    run_serialmgr()
