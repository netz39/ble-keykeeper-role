import ble_helpers


def test_addr_to_str():
    addr = b"\xde\xad\xbe\xef\xae\xea"
    assert ble_helpers.addr_to_str(addr) == "EA:AE:EF:BE:AD:DE"


def test_str_to_addr():
    addr_str = "01:23:45:67:89:AB"
    assert ble_helpers.str_to_addr(addr_str) == b"\xab\x89\x67\x45\x23\x01"


def test_reversability():
    addr_strings = ['F8:4C:B0:F1:5A:43',
                    'C0:DC:EF:35:51:41',
                    'DC:44:E5:74:44:A3',
                    'D8:79:35:52:27:C7',
                    'CF:66:64:C4:7F:83',
                    'C4:8B:42:80:CC:CA',
                    'E3:80:90:85:2F:01',
                    'CF:92:E8:4B:BA:02',
                    'F5:82:EE:81:1F:07',
                    'F7:62:32:06:D0:AA']
    for addr_str in addr_strings:
        addr = ble_helpers.str_to_addr(addr_str)
        assert addr_str == ble_helpers.addr_to_str(addr)


def test_reversability2():
    key_strings = ['07B3DE4C79D3E852037F264462318C1C',
                   '7F11F4205161BBAC7BE8ABAD47CD7ECB',
                   'D9256FD1F95E5EC214DB0A7FA8644494',
                   '15FCFD5C407BEFC3F72AA9EBED02AED4',
                   '4D10EE86D498F0F5FE6E2BF98D51E521',
                   'A05B95D26E8E887D1D3B8C64CEFB08CC',
                   '94FAE1FDA67219186FC7E0B94F335A17',
                   'E3888F4C72DF5FE81CBADA31192AF8EE',
                   '8DFF2783B769BBED09F40DAF0402AB65',
                   '72106F6C686F728E63FD114FF10F1235']

    for key_str in key_strings:
        key = ble_helpers.str_to_key(key_str)
        assert key_str == ble_helpers.key_to_str(key)
