# Battery Carrier Board

Carrier for a TP4056 charging module (with DW01A/FS8205A protection), adding
battery-voltage sensing and connectorised power for the Waveshare e-Paper ESP32
Driver Board.

Replaces the 18650 V8 shield, which wastes ~4-5 mA boosting 3.7 V to 5 V only for
the Waveshare regulator to drop it back down. The `5V` pin accepts 3.6-5.5 V, so
the cell drives it directly.

Board: 60 x 30 mm, 2 layer, 1.6 mm. Signals on F.Cu, ground pour on B.Cu.

## Netlist

| Net | Connections |
|---|---|
| `BAT+`   | J1.1, U1:B+ |
| `BAT-`   | J1.2, U1:B- |
| `VOUT`   | U1:OUT+, SW1.1 |
| `VSW`    | SW1.2, R1.2, C2.1, C3.2, J2.1, TP1 |
| `VSENSE` | R1.1, R2.2, C1.2, J2.3, TP2 |
| `GND`    | U1:OUT-, R2.1, C1.1, C2.2, C3.1, J2.2 |

Load is taken from the module's `OUT+`/`OUT-`, through the protection FETs, never
from `B+`/`B-`, which would bypass over-discharge protection entirely.

`J2` pinout, to the Waveshare board: **1 = 5V, 2 = GND, 3 = GPIO34**.

## Bill of materials

| Ref | Value | Package | Notes |
|---|---|---|---|
| U1 | TP4056 module w/ protection | 26 x 17 mm | On hand, board marking 03962A |
| J1 | JST-PH 2-pin | B2B-PH-K-S | 18650 cell in |
| J2 | JST-PH 3-pin | B3B-PH-K-S | To Waveshare 5V / GND / GPIO34 |
| SW1 | SPST slide | DIP slide, 9.78 x 4.72 mm | In the VOUT line |
| R1 | 100k 1% | 0805 | Divider high side |
| R2 | 100k 1% | 0805 | Divider low side |
| C1 | 100nF X7R | 0805 | ADC sampling reservoir |
| C2 | 220uF 10V | CP_Elec_6.3x3.9 | Bulk, transient support |
| C3 | 10uF X5R 16V | 0805 | HF decoupling |
| TP1/TP2 | test pads | THT 1.5 mm | VSW / VSENSE, for ADC calibration |
| H1/H2 | mounting | M2.5 | Board-only, not in the schematic |

1% resistors keep the divider ratio error near 1%; firmware trims the rest against
a multimeter reading.

## Design notes

**Divider sits after SW1**, so it draws nothing when switched off. Standing drain
when on is 4.2 V / 200k = **21 uA**, about 3% of the ~700 uA system budget.

**Divider ratio is 2:1.** A 4.2 V cell presents 2.10 V at `VSENSE`; the 3.6 V
regulator-dropout floor presents 1.80 V. Both sit inside ADC1's usable range at
11 dB attenuation. Firmware doubles the reading.

**GPIO34 is on ADC1**, which is required: ADC2 is unavailable while WiFi is
active. GPIO 34/35/36/39 are the pins the 12.48in panel driver leaves free, and
all are input-only, which suits a sense line.

**C2/C3 are deliberate.** The cell now sits behind a JST lead and the protection
MOSFETs, and WiFi TX pulls 150 mA+ in bursts. Local bulk keeps those transients
off the rail.

**Layout.** The module lies flat over the left of the board and mates through its
four edge pads, so every other part sits to its right and nothing is trapped
underneath. J1 is hard against the module's B+/B- pads to keep those tracks
short. VSW runs down the left corridor at x=46 and VSENSE down the right at
x=58, so the two never cross and no signal needs the back layer.

## Verification

`kicad-cli` reports, on the committed files:

| Check | Result |
|---|---|
| DRC violations | 0 |
| Unconnected items | 0 |
| Schematic parity | 0 |
| ERC violations | 0 |

## Module pad spacing

The four pads are **not evenly spaced**. Two tight pairs, with a wide gap in the
middle where the `B+` / `B-` silkscreen goes:

```
  OUT+  --.
          |  3.175 mm  (1/8", exact)
  B+    --'
          |
          |  7.600 mm  (0.2992" -- near but not exactly 0.300")
          |
  B-    --.
          |  3.175 mm  (1/8", exact)
  OUT-  --'
             total span 13.950 mm
```

Pad copper is ~2.40 mm square; holes ~1.0 mm.

### How these numbers were arrived at

The outer pairs are unambiguous: a scaled photo of the module puts them at
3.10 and 3.25 mm (mean 3.20), and 1/8" = 3.175 sits inside that. Taken as exact.

The middle gap is the uncertain one. Three independent routes:

| Route | Middle centre-to-centre |
|---|---|
| Scaled photo, self-consistent | 7.55 mm |
| 14.0 mm caliper span across outer pad centres, minus 2 x 1/8" | 7.65 mm |
| 5.0 mm caliper gap between the middle pads, plus pad height | ~7.55 mm |

They agree to within 0.1 mm, and **7.600 is used as the midpoint**. 0.300"
(7.62) also falls inside the window -- the measurements cannot separate a
genuine 0.300" design from a slightly-off-imperial one.

Two things are worth recording because they are easy to get wrong:

- **Solder overhang cancels out of centre-to-centre.** Solder bulging past the
  copper makes a caliper read the gap smaller and the pad larger by the same
  amount. So a measured gap may only be combined with a pad height measured *the
  same way*; mixing a caliper gap with a photo-derived copper pad height
  double-counts the overhang and produces a spuriously low pitch (7.40 mm).
- **Edge-threshold choice cancels out too.** Sweeping the copper/soldermask
  threshold from 0.4 to 0.8 moves pad height and edge gap in opposite
  directions; their sum stays at 7.55-7.57 mm. That sum is the robust quantity.

### Why the residual uncertainty does not matter

The pad holes are drilled **1.3 mm** rather than the 1.1 mm a snug fit would
want. A 0.64 mm square header pin then has 0.33 mm of radial slack -- more than
the +/-0.05 mm the middle pitch is uncertain by, with margin left over. The
2.2 mm pads keep a 0.45 mm annular ring, well inside fab minimums.

An earlier revision assumed even 4.667 mm spacing. That was wrong by 2.9 mm per
gap and would not have fitted at all.

To re-cut the footprint with different gaps, pass them as a comma list; the board
and its routing follow from the new pad positions:

```sh
python3 gen_footprint.py 3.175,7.62,3.175    # footprint
<kicad-python> gen_board.py                  # board follows
python3 gen_sch.py                           # schematic
```

The pad-column-to-board-edge offset (2.0 mm) is cosmetic only -- it positions the
silkscreen outline, not the pads.

## Files

| Path | What |
|---|---|
| `battery-carrier.kicad_pro/.kicad_sch/.kicad_pcb` | KiCad project |
| `epcal.pretty/`, `epcal.kicad_sym` | Project footprint and symbol for the module |
| `gerbers/battery-carrier-gerbers.zip` | Fab package (Gerber X2 + Excellon) |
| `schematic.pdf`, `board-top.png`, `bom.csv` | Review artifacts |
| `gen_footprint.py`, `gen_board.py`, `gen_sch.py` | Generators; the board is reproducible from these |
