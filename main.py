# main.py - WiFi + public IP + MAC + running time for ESP32-S3 Pico + Nokia 5110
# Requires: pcd8544.py on the driver
# Fill in WIFI_SSID and WIFI_PASS.

import time
import network
import usocket as socket
from machine import Pin, SPI
from pcd8544 import PCD8544

# === Edit these ===
WIFI_SSID = "WIFI_SSID"
WIFI_PASS = "WIFI_PASS"

# === Pins (match your wiring) ===
PIN_SCLK = 18
PIN_DIN  = 17
PIN_DC   = 2
PIN_CS   = 5
PIN_RST  = 15

# === Display helpers ===
spi = SPI(1, baudrate=4_000_000, polarity=0, phase=0,
          sck=Pin(PIN_SCLK), mosi=Pin(PIN_DIN))
cs  = Pin(PIN_CS, Pin.OUT)
dc  = Pin(PIN_DC, Pin.OUT)
rst = Pin(PIN_RST, Pin.OUT)
lcd = PCD8544(spi, cs, dc, rst)

# Because LCD width is small, limit chars per line to a safe value:
MAX_CHARS = 14  # safe approx for 84px width with default font

def fit_text(s, n=MAX_CHARS):
    s = str(s)
    if len(s) <= n:
        return s
    # prefer to keep start and end if it contains meaningful ending (e.g., IP)
    # but for simplicity: truncate with ellipsis
    return s[:n-1] + "…"

def show_lines(lines):
    lcd.fill(0)
    y = 0
    for i, ln in enumerate(lines):
        ln = fit_text(ln)
        lcd.text(ln, 0, y)
        y += 10
    lcd.show()

# === Wi-Fi connection ===
def wifi_connect(ssid, pwd, timeout=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan
    wlan.connect(ssid, pwd)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            return None
        time.sleep(1)
    return wlan

# === Get MAC (formatted) ===
def get_mac_str(wlan):
    try:
        mac = wlan.config('mac')  # returns bytes
        return ':'.join('{:02X}'.format(b) for b in mac)
    except:
        return "MAC:N/A"

# === Get public IP using a lightweight HTTP GET (api.ipify.org) ===
def get_public_ip(timeout=5):
    try:
        addr_info = socket.getaddrinfo("api.ipify.org", 80)
        if not addr_info:
            return None
        addr = addr_info[0][-1]
        s = socket.socket()
        s.settimeout(timeout)
        s.connect(addr)
        req = b"GET /?format=text HTTP/1.0\r\nHost: api.ipify.org\r\n\r\n"
        s.send(req)
        # read and discard headers, then read body
        data = b""
        # Read until we find double CRLF (end of headers)
        while True:
            chunk = s.recv(64)
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data:
                break
        if not data:
            s.close()
            return None
        # split header and body
        parts = data.split(b"\r\n\r\n", 1)
        body = parts[1] if len(parts) > 1 else b""
        # If there's more body to read, read rest
        # (ip string is short so probably already present)
        # try to read remainder quickly
        try:
            while True:
                more = s.recv(64)
                if not more:
                    break
                body += more
        except:
            pass
        s.close()
        # body may include whitespace/newline
        ip = body.decode().strip().splitlines()[0]
        # basic validation
        if len(ip) > 0:
            return ip
        return None
    except Exception as e:
        try:
            s.close()
        except:
            pass
        return None

# === Main program ===
def main():
    lcd.fill(0)
    lcd.text("Booting...", 0, 0)
    lcd.show()
    time.sleep(1)

    wlan = wifi_connect(WIFI_SSID, WIFI_PASS, timeout=20)
    if not wlan:
        show_lines(["Wi-Fi failed", "Check creds", "", ""])
        return

    ssid = wlan.config('essid') if hasattr(wlan, 'config') else WIFI_SSID
    mac = get_mac_str(wlan)
    local_ip = wlan.ifconfig()[0]

    # Try fetch public IP once at start
    public_ip = get_public_ip() or "IP:N/A"

    # Lines: SSID, MAC, PUBLIC IP, running time (updates)
    # Running-time updates every second, public IP refresh every few minutes
    show_all = True  # set to False to alternate screens instead
    public_ip_refresh_interval = 300  # seconds (5 min)
    last_public_ip_refresh = time.time()

    # main loop
    while True:
        # refresh public IP occasionally
        if time.time() - last_public_ip_refresh > public_ip_refresh_interval:
            new_ip = get_public_ip()
            if new_ip:
                public_ip = new_ip
            last_public_ip_refresh = time.time()

        # current local time (apply timezone offset if desired)
        # Note: MicroPython RTC may be unset; we show relative running time if RTC not set.
        try:
            tm = time.localtime()
            date_str = "{:04d}-{:02d}-{:02d}".format(tm[0], tm[1], tm[2])
            time_str = "{:02d}:{:02d}:{:02d}".format(tm[3], tm[4], tm[5])
            time_line = time_str
        except:
            # fallback, show uptime
            uptime = int(time.ticks_ms() / 1000)
            time_line = "Up:{}s".format(uptime)

        if show_all:
            # Build lines and display
            line1 = "WiFi:" + ssid
            line2 = "MAC:" + mac
            line3 = "PubIP:" + public_ip
            line4 = time_line
            show_lines([line1, line2, line3, line4])
            time.sleep(1)  # update every second (time refresh)
        else:
            # Alternate between info screen and time screen (if you prefer)
            show_lines(["WiFi:" + ssid, "MAC:" + mac, "PubIP:" + public_ip, ""])
            time.sleep(4)
            show_lines([date_str, time_line, "", "ESP32-S3 Pico"])
            time.sleep(2)

# Run
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # show the short error on screen and re-raise for REPL
        try:
            lcd.fill(0)
            lcd.text("Error:", 0, 0)
            lcd.text(str(e)[:14], 0, 10)
            lcd.show()
        except:
            pass
        raise
