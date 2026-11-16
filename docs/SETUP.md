# Setup

Python 3.10 or newer is recommended for the repository checks. Scripts use the standard library. Hardware work was performed on Raspberry Pi OS Bookworm; interactive stdin/select behaviour is intended for Linux terminals, including SSH, not Windows native execution.

Start offline:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/fx100_supervised_bench_8s.py
```

Default invocation only prints instructions. Hardware execution is explicit and requires reading the script's props-off procedure. These are bench tools, not a flight-ready application.

Keep the Pi's home-network connection separate from the drone adapter. Configure the drone network through NetworkManager using your own SSID and credentials. Verify the correct interface with `iw dev` and its connection with `iw dev wlan1 link`. Never publish a Wi-Fi password or decrypted raw capture.

The scripts use drone address 192.168.0.1:50000 and bind a route-derived local address on port 5010. Confirm these match your hardware. Close other sender programs before any bench session. A VPN on the development laptop previously blocked SSH; check local-network access before changing the Pi's configuration.

Generated JSONL logs are written to the user's home directory and ignored by this repository. Record whether props were removed, the physical setup, battery condition, observed motor behaviour and whether landing was manual or automatic alongside every run.
