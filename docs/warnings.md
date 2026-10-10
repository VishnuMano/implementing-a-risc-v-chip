# Reviewed baseline warnings

The first SKY130 run reports 504 lint warnings, with zero lint errors and zero
inferred latches. This is not a zero-warning build. Its breakdown is:

| Category | Count | Interpretation |
| --- | ---: | --- |
| TIMESCALEMOD | 446 | PDK blackbox declarations lack the timescale present in the CPU source; no RTL delay controls are used |
| BLKSEQ | 21 | Blocking assignments in the pinned upstream CPU implementation |
| UNUSEDSIGNAL | 15 | Unused CPU features and unused UART input bits |
| PINCONNECTEMPTY | 13 | Intentionally unused optional CPU outputs |
| GENUNNAMED | 7 | Unnamed upstream generate blocks |
| WIDTHTRUNC | 2 | UART's 32-bit divider expression assigned to its 16-bit counter; the configured value is 86 and fits exactly |

PicoRV32 is kept unmodified. The UART divider must remain in 1–65536; parameter
validation and fully sized expressions are a follow-up cleanup. Both the RTL
and generic netlist pass the same UART frame and firmware checks.

Physical-tool warnings include duplicate Liberty loads during timing repair,
partial support for LEF58 rules, and high-fanout nets. These warnings are retained
in the full run reports. Routing's own check is distinct from final Magic and
KLayout DRC, so router convergence alone does not establish final DRC status.

The default IR-drop setup has no package-specific voltage-source locations.
It is not a validated chip-level power-integrity analysis. Do not interpret this
core layout as a manufacturing-ready standalone die.
