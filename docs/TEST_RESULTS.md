# Test evidence

Prepared 16 November 2026 from the project discussion and previously inspected recordings. Raw captures and telemetry remain private; this is an aggregate evidence summary, not an independently reproducible public dataset.

| Evidence | Result | Scope |
|---|---|---|
| Original extraction | 2,595 TX messages, 2,592 standard 17-byte controls | All standard control checksums matched |
| Labelled app recording | 4,905 decoded UDP rows | Unlock, takeoff and landing correlated with deliberate actions |
| Initial Pi probe | 5 TX, 191 valid replies | No motor movement reported |
| Charged run, 11 Nov 15:38 | 161 TX, 529 RX, all frame/checksum checks passed | Status 00 → 08 → 10 → 00; motor response reported |
| Extended runs, 11 Nov 17:32–17:39 | Four logs with five-second centred intervals | Status transitions and centred commands inspected |
| 12 Nov 10:14 run | 164 TX, 623 RX, all checks passed | Initially described as stationary; operator corrected to props-on flight |
| Unlock-only manual landing | Screenshot showed input-triggered LAND and return to 00 | Operator reported prompt motor stop |
| Unlock-only automatic landing | Operator reported success | No independently analysed log for this assertion |
| Supervised five-second manual landing | Screenshot: 160 TX, 463 valid replies, 10 → 00 | Input-triggered LAND shown |
| Supervised five-second timeout | Operator reported success | Automatic path reported |
| Eight-second version | Operator reported stable height in net enclosure and both landing paths | Latest flight logs not yet supplied for independent analysis |

## Charged run timing

Relative to script start: unlock begins 2.001 s; status 08 at 2.011 s; takeoff begins 5.002 s; status 10 at 5.055 s; landing begins 8.002 s; status 00 at 10.326 s.

## Important correction

The 12 November 10:14 log cannot be used as a stationary calibration baseline. The operator later confirmed propellers were fitted and the drone rose to about 1.2 m, held briefly and landed. The earlier inference that candidate altitude changed without movement was therefore withdrawn.

## Offline validation

Repository tests validate packet integrity, conservative gating and cleanup decisions using fake links. CI never opens a drone socket or starts a hardware sequence. Earlier development included localhost UDP simulations. Offline tests do not prove physical flight safety, timing under load or network-failure recovery.
