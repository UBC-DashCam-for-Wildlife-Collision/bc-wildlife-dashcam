# GPS Interface Specification
**Module:** u-blox NEO-M8N  
**Author:** Aditya Patel  
**Date:** May 13, 2026  
**Status:** Draft v1.0

---

## 1. UART Configuration

| Parameter | Value |
|---|---|
| Baud Rate | 9600 bps |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Format | 8N1 |
| Connection | NEO-M8N TX pin → Raspberry Pi GPIO 15 (RX) |
| Output Rate | 1 Hz (default) |

---

## 2. NMEA Sentence Parsed

Sentence type: GPRMC (Recommended Minimum Specific GPS Data)

This is the only sentence parsed. All other NMEA sentences output by the module are ignored.

Example raw sentence:

```
