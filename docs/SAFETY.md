# Bench-only code and known limits

All included executable motor sequences retain their props-off prompts. An acknowledgement is a human check, not a physical interlock. No repository command is an approval for free flight.

- Landing depends on the same Wi-Fi link as other commands. Reply monitoring cannot guarantee recovery after link loss.
- ENTER is a landing request, not an independent emergency stop. Terminal EOF also triggers this branch.
- Status 10 is an observed association, not an altitude or hover guarantee.
- There is no decoded and validated altitude ceiling, collision avoidance or geographic boundary.
- A stopped process, lost power or failed socket can prevent cleanup packets from arriving.
- Cleanup attempts landing for a bounded interval. It does not automatically prove motor shutdown.
- Buffered logs may be lost if the process is killed or power is lost.
- The source IP and XOR check validate expected framing, not cryptographic authenticity.
- Historical scripts differ in safeguards. The latest monitored variants are clearly named; older scripts are preserved for provenance.
- Do not reach toward, catch or hand-hold an aircraft with spinning propellers.

The project owner's enclosed flight reports are evidence of those individual outcomes only. Loss-of-link behaviour and independent emergency recovery are still unresolved.
