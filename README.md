# BLE Keykeeper Ansible Role
This is the server part of [BLE Coin](https://github.com/maz3max/ble-coin), which allows you to run a script when a user authenticates. Using this service, you will never have to manually use the central's serial interface, everything in that regard will be handled by the service.

## Quick Start Guide

### 0 - Obtain Hardware
  1. Take a look at the [project page](https://github.com/maz3max/ble-coin) for more info.
  2. A Raspberry Pi is also recommended.

### 1 - Prepare central
  1. Download [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-desktop) and install the Programmer App.
  2. Download the [newest release](https://github.com/maz3max/ble-coin/releases) of the firmware files.
  3. Flash the `central.hex` onto your [NRF52840 dongle](https://www.nordicsemi.com/?sc_itemid=%7BCDCCA013-FE4C-4655-B20C-1557AB6568C9%7D).

### 2 - Get ready to flash coins
  1. Look [here](https://github.com/maz3max/ble-coin/tree/master/coin) for more advice.

### 3 - Install dependencies
  1. Install [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html).

### 4 - Run the role
  1. Set up a playbook and inventory
  2. Make sure you have set the `door_open_command` and `ble_keykeeper_dir` variables to appropriate values.
  3. Run your playbook

### 5 - Try it out
  1. Make sure the [NRF52840 dongle](https://www.nordicsemi.com/?sc_itemid=%7BCDCCA013-FE4C-4655-B20C-1557AB6568C9%7D) is connected to the server.
  2. Navigate to your `ble_keykeeper_dir` and create a new coin with `./ble_gen_coin.py winnie`. You can change `winnie` to any name you like (no spaces).
  3. Flash the newly created `coin_xxxxxxxxxxxx.hex` onto you coin. You can delete the file after.
  4. Restart the service using `systemctl restart ble-keykeeper.service`
  5. Press the button on your coin. Does it blink? If yes, it found the central.
  6. Check the service logs with `journalctl -u ble-keykeeper.service`. Scroll to the bottom - do you see something like [INFO:root:winnies's coin (100%🔋) authenticated]?

## Tips and Tricks
  * The service uses a very simple database to save all the required names and keys. It is saved in the `central.txt`, `coins.txt` and `names.txt` files.
  * Every line in `coins.txt` represents a coin as a space-separated tuple of (address, irk, ltk, spacekey). If you remove a line and restart the service, the respective coin will no longer be able to connect.
  * Each line in `names.txt` represents an optional name for a coin's address as a space-separated tuple of (address, name). Edit as you like - it will not affect authentication - but don't break the format. Changes will only be applied on service restart.
