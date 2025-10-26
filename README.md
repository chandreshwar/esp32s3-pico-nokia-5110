A simple implementation of WiFi and Time on ESP32S3 Pico Board written in micropython. The Pin configuration that I used is:

| Nokia 5110 | ESP32-S3 Pico | Note                |
| ---------- | ------------- | ------------------- |
| RST        | GPIO 15       | Reset               |
| CE (CS)    | GPIO 5        | Chip Select         |
| DC         | GPIO 2        | Data/Command        |
| DIN        | GPIO 17       | MOSI                |
| CLK        | GPIO 18       | SCK                 |
| VCC        | 3.3V          | Power               |
| BLK        | 3.3V          | Backlight always on |
| GND        | GND           | Ground              |

The text is overflowing at the moment. Both the driver (pcd8544.py) and the main.py need to be on your ESP32S3-Pico and Micropython has to be burnt on it. You can use [Thonny](https://thonny.org).
