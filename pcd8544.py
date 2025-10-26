# pcd8544.py - robust MicroPython driver for Nokia 5110 (PCD8544)
# Tries multiple framebuf formats and gives clearer errors.

from machine import Pin, SPI
import framebuf
import time

class PCD8544(framebuf.FrameBuffer):
    def __init__(self, spi, cs, dc, rst):
        # Basic argument validation
        if spi is None:
            raise ValueError("spi is None - provide an SPI object")
        if cs is None or dc is None or rst is None:
            raise ValueError("cs, dc and rst must be Pin objects")

        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst

        self.width = 84
        self.height = 48
        buf_len = (self.width * self.height) // 8
        self.buffer = bytearray(buf_len)

        # Try common monochrome formats; clearer error if none work
        tried = []
        for fmt in (framebuf.MONO_HLSB, framebuf.MONO_VLSB):
            try:
                super().__init__(self.buffer, self.width, self.height, fmt)
                self._framebuf_format = fmt
                break
            except Exception as e:
                tried.append((fmt, str(e)))
        else:
            # No format worked
            raise ValueError("FrameBuffer init failed for formats tried: {}\n"
                             "buffer_len={} width={} height={}"
                             .format(tried, buf_len, self.width, self.height))

        # init GPIO defaults
        self.cs.init(self.cs.OUT)
        self.dc.init(self.dc.OUT)
        self.rst.init(self.rst.OUT)

        self.reset()
        self.init_display()

    def reset(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

    def init_display(self):
        # PCD8544 initialization sequence
        self.cmd(0x21)  # Extended instructions
        self.cmd(0xBf)  # Vop (contrast) - tweak if needed
        self.cmd(0x04)  # Temperature coefficient
        self.cmd(0x14)  # Bias system
        self.cmd(0x20)  # Basic instructions
        self.cmd(0x0C)  # Normal display mode

    def cmd(self, c):
        self.cs.value(0)
        self.dc.value(0)  # command
        self.spi.write(bytearray([c]))
        self.cs.value(1)

    def data(self, b):
        self.cs.value(0)
        self.dc.value(1)  # data
        self.spi.write(b if isinstance(b, (bytes, bytearray)) else bytearray([b]))
        self.cs.value(1)

    def show(self):
        # Send the buffer in 6 rows of 8-pixel-high pages (48 / 8 = 6)
        for page in range(6):
            self.cmd(0x40 | page)  # Set Y address of RAM
            self.cmd(0x80 | 0)     # Set X address to 0
            self.cs.value(0)
            self.dc.value(1)
            start = page * 84
            self.spi.write(self.buffer[start:start + 84])
            self.cs.value(1)
