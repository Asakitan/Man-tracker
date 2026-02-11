
import socket
import struct
import random
import threading
import time
from typing import Optional, Tuple
from dataclasses import dataclass


# ─── Command codes ───

CMD_CONNECT      = 0xAF3C2828
CMD_MOUSE_MOVE   = 0xAEDE7345
CMD_MOUSE_LEFT   = 0x9823AE8D
CMD_MOUSE_MIDDLE = 0x97A3AE8D
CMD_MOUSE_RIGHT  = 0x238D8212
CMD_MOUSE_WHEEL  = 0xFFEEAD38
CMD_MOUSE_AUTO   = 0xAEDE7346   # Device-side interpolated move
CMD_KEYBOARD_ALL = 0x123C2C2F
CMD_REBOOT       = 0xAA8855AA
CMD_BAZER_MOVE   = 0xA238455A   # Bezier curve move
CMD_MONITOR      = 0x27388020
CMD_MASK_MOUSE   = 0x23234343
CMD_UNMASK_ALL   = 0x23344343
CMD_SETCONFIG    = 0x1D3D3323

# ─── Error codes ───

ERR_NONE         = 0
ERR_SOCKET       = -9000
ERR_NET_TX       = -8998
ERR_NET_TIMEOUT  = -8997
ERR_NET_CMD      = -8996
ERR_NET_PTS      = -8995

# ─── Header format: mac(I) + rand(I) + indexpts(I) + cmd(I) = 16 bytes, little-endian ───

HEADER_FMT = "<IIII"
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 16

# ─── soft_mouse_t: button(i) + x(i) + y(i) + wheel(i) + point[10](10i) = 56 bytes ───

MOUSE_FMT = "<iiiiiiiiiiiiii"  # 14 ints = 56 bytes
MOUSE_SIZE = struct.calcsize(MOUSE_FMT)  # 56

PACKET_SIZE = HEADER_SIZE + MOUSE_SIZE  # 72 bytes


@dataclass
class KmboxConfig:
    """KMBOX-NET configuration"""
    enabled: bool = False
    ip: str = "192.168.2.188"
    port: int = 8312
    mac: str = "12345678"       # 8-digit hex MAC shown on device LCD
    timeout: float = 0.5        # Receive timeout (seconds)


class KmboxNetDevice:
    """
    KMBOX-NET device driver

    Usage:
        dev = KmboxNetDevice(config)
        if dev.connect():
            dev.move(10, -5)      # Relative move
            dev.left_down()       # Left button down
            dev.left_up()         # Left button up
        dev.close()
    """

    def __init__(self, config: KmboxConfig):
        self.config = config
        self._sock: Optional[socket.socket] = None
        self._mac_int: int = self._parse_mac(config.mac)
        self._index: int = 0
        self._button_state: int = 0  # Current button bitmask
        self._connected: bool = False
        self._lock = threading.Lock()

    # ── Connect / Disconnect ──

    def connect(self) -> bool:
        """Connect to KMBOX-NET device; returns True on success"""
        try:
            self.close()
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.settimeout(self.config.timeout)
            self._index = 0

            # Send handshake packet (16-byte header only)
            header = self._build_header(CMD_CONNECT)
            self._sock.sendto(header, (self.config.ip, self.config.port))

            # Wait for response
            try:
                data, _ = self._sock.recvfrom(256)
                if len(data) >= HEADER_SIZE:
                    rx_mac, rx_rand, rx_idx, rx_cmd = struct.unpack_from(HEADER_FMT, data)
                    if rx_cmd == CMD_CONNECT:
                        self._connected = True
                        print(f"[KMBOX-NET] Connected to {self.config.ip}:{self.config.port}")
                        return True
                    else:
                        print(f"[KMBOX-NET] Handshake response command mismatch: 0x{rx_cmd:08X}")
                else:
                    print(f"[KMBOX-NET] Handshake response too short: {len(data)} bytes")
            except socket.timeout:
                print("[KMBOX-NET] Handshake timed out, device not responding")
            except Exception as e:
                print(f"[KMBOX-NET] Handshake error: {e}")

            self._connected = False
            return False

        except Exception as e:
            print(f"[KMBOX-NET] Connection failed: {e}")
            self._connected = False
            return False

    def close(self):
        """Close connection"""
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._sock is not None

    def test_move(self) -> bool:
        """Send a small test move to verify device actually responds."""
        if not self.is_connected:
            return False
        # Use CMD_MOUSE_LEFT with x/y to test movement (most compatible)
        ok1 = self._send_mouse_cmd(CMD_MOUSE_LEFT, x=10, y=0, button_override=0)
        time.sleep(0.05)
        ok2 = self._send_mouse_cmd(CMD_MOUSE_LEFT, x=-10, y=0, button_override=0)
        print(f"[KMBOX-NET] test_move: +10={ok1} -10={ok2}")
        return ok1 and ok2

    # ── Mouse operations ──

    def move(self, dx: int, dy: int) -> bool:
        """
        Send relative mouse move.
        Uses CMD_MOUSE_LEFT with current button state + x/y offset
        for maximum firmware compatibility.

        Parameters
        ----------
        dx : int  Relative X offset
        dy : int  Relative Y offset

        Returns
        -------
        bool  Whether send succeeded
        """
        if not self.is_connected:
            return False
        # Use CMD_MOUSE_LEFT for all movement – carries button state + x/y
        # in the same soft_mouse_t struct. Known to work on this firmware.
        return self._send_mouse_cmd(CMD_MOUSE_LEFT, x=dx, y=dy,
                                     button_override=self._button_state)

    def move_auto(self, dx: int, dy: int, ms: int = 100) -> bool:
        """
        Device-side interpolated move (smoother, device completes move in ms milliseconds).

        Parameters
        ----------
        dx, dy : int  Target relative offset
        ms : int      Move duration (milliseconds)
        """
        if not self.is_connected:
            return False
        # Fallback: also use CMD_MOUSE_LEFT if CMD_MOUSE_AUTO doesn't work
        return self._send_mouse_cmd(CMD_MOUSE_AUTO, x=dx, y=dy, rand_override=ms,
                                     button_override=self._button_state)

    def left_down(self) -> bool:
        if not self.is_connected:
            return False
        self._button_state |= 0x01
        return self._send_mouse_cmd(CMD_MOUSE_LEFT, button_override=self._button_state)

    def left_up(self) -> bool:
        self._button_state &= ~0x01
        if not self.is_connected:
            return False
        return self._send_mouse_cmd(CMD_MOUSE_LEFT, button_override=self._button_state)

    def left_click(self, duration_ms: float = 50):
        """Left click with move freeze (x=0, y=0)"""
        if not self.is_connected:
            return False
        self._button_state |= 0x01
        self._send_mouse_cmd(CMD_MOUSE_LEFT, button_override=self._button_state)
        time.sleep(duration_ms / 1000.0)
        self._button_state &= ~0x01
        self._send_mouse_cmd(CMD_MOUSE_LEFT, button_override=self._button_state)
        return True

    def right_down(self) -> bool:
        if not self.is_connected:
            return False
        self._button_state |= 0x02
        return self._send_mouse_cmd(CMD_MOUSE_RIGHT, button_override=self._button_state)

    def right_up(self) -> bool:
        self._button_state &= ~0x02
        if not self.is_connected:
            return False
        return self._send_mouse_cmd(CMD_MOUSE_RIGHT, button_override=self._button_state)

    def right_click(self, duration_ms: float = 50):
        """Right click"""
        if not self.is_connected:
            return False
        self.right_down()
        time.sleep(duration_ms / 1000.0)
        self.right_up()
        return True

    def middle_down(self) -> bool:
        if not self.is_connected:
            return False
        self._button_state |= 0x04
        return self._send_mouse_cmd(CMD_MOUSE_MIDDLE, button_override=self._button_state)

    def middle_up(self) -> bool:
        self._button_state &= ~0x04
        if not self.is_connected:
            return False
        return self._send_mouse_cmd(CMD_MOUSE_MIDDLE, button_override=self._button_state)

    def wheel(self, delta: int) -> bool:
        """Scroll wheel (positive=up, negative=down)"""
        return self._send_mouse_cmd(CMD_MOUSE_WHEEL, wheel=delta)

    # ── Internal methods ──

    def _parse_mac(self, mac_str: str) -> int:
        """Parse 8-digit hex MAC string to uint32"""
        mac_str = mac_str.strip().replace(":", "").replace("-", "")
        if len(mac_str) != 8:
            raise ValueError(f"Invalid MAC format, expected 8 hex digits: '{mac_str}'")
        b = bytes.fromhex(mac_str)
        return (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]

    def _build_header(self, cmd: int, rand_override: Optional[int] = None) -> bytes:
        """Build 16-byte packet header"""
        self._index += 1
        rand_val = rand_override if rand_override is not None else random.randint(0, 0xFFFFFFFF)
        return struct.pack(HEADER_FMT, self._mac_int, rand_val, self._index, cmd)

    def _send_mouse_cmd(
        self,
        cmd: int,
        x: int = 0,
        y: int = 0,
        wheel: int = 0,
        rand_override: Optional[int] = None,
        button_override: Optional[int] = None,
    ) -> bool:
        """Send mouse command (header + soft_mouse_t)"""
        with self._lock:
            try:
                header = self._build_header(cmd, rand_override)
                # Use explicit button value if provided, otherwise 0
                # (matches original KMBOX SDK: each command clears struct first)
                btn = button_override if button_override is not None else 0
                # soft_mouse_t: button, x, y, wheel, point[0..9]
                mouse_data = struct.pack(
                    MOUSE_FMT,
                    btn, x, y, wheel,
                    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  # point[0..9]
                )
                packet = header + mouse_data
                self._sock.sendto(packet, (self.config.ip, self.config.port))
                return True
            except Exception as e:
                print(f"[KMBOX-NET] Send failed: {e}")
                self._connected = False
                return False

    # ── Context manager ──

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()
