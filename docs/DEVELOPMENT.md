# Development history

1. Connected a Raspberry Pi to the drone-hosted 5 GHz access point and established IP connectivity.
2. Captured original-app traffic, decrypted the owner's recordings and extracted controller payloads.
3. Identified the dominant 17-byte frame and XOR integrity rule.
4. Corrected initial packet-offset and client-port assumptions.
5. Recorded deliberate app actions to label unlock, takeoff and landing.
6. Built bounded probe, unlock and takeoff bench clients with JSONL records.
7. Compared failed runs with charged-battery successes rather than treating UDP send completion as command acceptance.
8. Extended the centred-control interval from two to five seconds. Operator reported airborne settling near the app's stated automatic takeoff height.
9. Added ENTER-to-land, status freshness checks, stale-reply monitoring and automatic timeout.
10. Extended the supervised interval to eight seconds. Operator reported enclosed stable-height flights and successful manual/automatic landing.

The original app displayed an automatic takeoff target of about 1.2 m and indoor mode with zero GPS satellites in a supplied screenshot. This is not evidence of GPS position hold. The Pi sends high-level commands; onboard stabilisation performs the actual flight control.

A 480 × 320 Tkinter touchscreen simulation was discussed separately. It is not integrated into these scripts. Video streaming, axis mapping and complete telemetry decoding were not completed.
