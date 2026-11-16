# Protocol findings

These are empirical observations from this drone and recordings, not a vendor specification. Byte indexes are zero-based.

## Transport and framing

Drone endpoint: UDP 50000 at 192.168.0.1. Client socket: UDP 5010. Client IP comes from the route, not a fixed previous DHCP address. Wi-Fi observed on channel 36 at 5180 MHz.

| Field | Observation |
|---|---|
| Byte 0 | TX 0x68, RX 0x58 |
| Byte 1 | Message type |
| Byte 2 | Length field; total frame length = value + 4 |
| Final byte | XOR of bytes 1 through the penultimate byte |
| Control header | 68 01 0d; total 17 bytes |
| Bytes 3–6 | Apparent axes; centre 80 80 80 80; mapping unresolved |
| Byte 7 | 20 in analysed standard controls |
| Byte 8 | Usually 08; startup variation 88 |
| Byte 9 | Labelled action flags |
| Byte 11 | Observed 00/01 variants; meaning unresolved |

Checksums matched all 2,592 standard packets in the original extraction. Correct framing does not establish command acceptance or authentication.

## Observed actions

| Byte 9 | Correlation |
|---|---|
| 00 | Centred/no action flag |
| 04 | Unlock |
| 08 | Takeoff |
| 10 | Landing |

Exact frames are retained in the source scripts. These mappings came from labelled original-app actions and subsequent hardware observations, rather than guessing from filenames.

In the labelled app recording, centred controls between takeoff and landing arrived about once per second. Action pulses arrived around 45–50 packets per second. This does not establish a universal required cadence for every mode.

## Incoming messages

| Prefix | Total length | Interpretation |
|---|---:|---|
| 58 8b 0f | 19 | Status with observed state associations |
| 58 8c 0d | 17 | Contains candidate height/speed fields; unverified |
| 58 9c 17 | 27 | Undecoded |
| 58 8a 0c | 16 | Contains identifier-like OR0181FXP text |

For 58 8b 0f, byte 12 correlated with 00 initial/stopped, 08 unlocked and 10 accepted takeoff. These associations are not a complete state specification, and 00 is not independent proof that motors physically stopped.

Candidate values in 58 8c 0d: little-endian bytes 11–12 rose from roughly 999/1000 to 1016 in several flight runs; signed byte 15 became positive on ascent and negative on descent. Units, reference and whether these are measured or commanded values remain unverified. Do not use them as altitude safety limits.

Bytes 11 and 14 in 58 8b 0f differed during depleted-battery failures. Charging restored response, supporting a battery-related explanation. Later successful runs also had nonzero byte 14: do not label it a simple battery warning or percentage.

## Corrections to early assumptions

Client port is 5010, not 50000. Action flags above are at byte 9, not byte 8. The startup byte-8 value 88 is not an established unlock command. Auxiliary outgoing frames 68 7e 1e, 68 0a 0f and 68 1b 08 have total lengths 34, 19 and 12 bytes. Their meanings remain unresolved. Early replay guesses are not included as validated procedures.
