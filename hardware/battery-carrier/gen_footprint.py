#!/usr/bin/env python3
"""Generate the TP4056 carrier's module footprint.

The module (board marking 03962A) presents its four pads in a single column on
one edge.  They are NOT evenly spaced: the two outer pairs are tight and a wide
gap in the middle makes room for the B+/B- silkscreen.

The two outer pairs are on a clean 1/8" (3.175mm) imperial pitch.  The middle
gap is NOT exact imperial: pinning the outer gaps at 1/8" and solving for it
independently gives 7.546mm from a scaled photo of the module and 7.650mm from a
caliper span across the outer pads -- straddling 0.300" (7.620) without landing
on it.  7.600mm (0.2992") sits 0.05mm from both, so that is what is used here.

Independent routes to that middle pitch land between 7.55 and 7.65mm (a scaled
photo gives 7.55; a 14.0mm caliper span across the outer pad centres implies
7.65; a 5.0mm caliper gap between the middle pads agrees with ~7.55 once solder
overhang is accounted for -- overhang shrinks the measured gap and grows the
measured pad by the same amount, so centre-to-centre is invariant to it).
0.300" (7.62) also sits inside that window.  7.600 is used as the midpoint.

Rather than chase the remaining +/-0.05mm, the pad holes are drilled 1.3mm
instead of 1.1mm.  That gives a 0.64mm header pin 0.33mm of radial slack, which
swallows the whole 7.55-7.65 uncertainty with margin to spare, and still leaves
a 0.45mm annular ring on the 2.2mm pads.

Override on the command line to re-cut the footprint:

    ./gen_footprint.py 3.2,7.6,3.2
"""
import uuid, sys

# Centre-to-centre gaps between consecutive pads, top -> bottom.
IN = 25.4
GAPS = ([float(v) for v in sys.argv[1].split(",")] if len(sys.argv) > 1
        else [0.125 * IN, 7.600, 0.125 * IN])

PAD_D, DRILL_D = 2.2, 1.3      # oversized drill absorbs the residual pitch uncertainty
SPAN = sum(GAPS)                                           # outer pad centres
BODY_L, BODY_W = 26.0, 17.0   # module PCB, excluding the corner horns
HORN = 1.5                    # horns extend this far past the right edge
EDGE_OFFSET = 2.0             # pad column to right edge; cosmetic (silk only)

PADS = ["OUT+", "B+", "B-", "OUT-"]      # top -> bottom, per silkscreen
assert len(GAPS) == len(PADS) - 1, "need one gap between each adjacent pad pair"

# Pad Y positions, centred on the column.
YS = [0.0]
for g in GAPS:
    YS.append(YS[-1] + g)
YS = [y - SPAN / 2.0 for y in YS]

def u():
    return str(uuid.uuid4())

x_right = EDGE_OFFSET
x_left = EDGE_OFFSET - BODY_L

out = ['(footprint "TP4056_Module_03962A"',
       '\t(version 20241229)',
       '\t(generator "epcal-gen")',
       '\t(generator_version "9.0")',
       '\t(layer "F.Cu")',
       '\t(descr "Carrier footprint for a TP4056 charging module with DW01A/FS8205A '
       'protection, board marking 03962A. Four unevenly spaced pads in one column, '
       '%.2fmm span, gaps %s mm. Module body %gx%gmm excluding corner horns.")'
       % (SPAN, "/".join("%g" % g for g in GAPS), BODY_L, BODY_W),
       '\t(tags "tp4056 battery charger module")',
       '\t(attr through_hole)']

for name, val, layer, y in (("Reference", "U**", "F.SilkS", -BODY_W / 2 - 1.5),
                            ("Value", "TP4056_Module_03962A", "F.Fab", BODY_W / 2 + 1.5)):
    out += [f'\t(property "{name}" "{val}"',
            f'\t\t(at 0 {y:.2f} 0)',
            f'\t\t(layer "{layer}")',
            f'\t\t(uuid "{u()}")',
            '\t\t(effects (font (size 1 1) (thickness 0.15)))',
            '\t)']

def rect(x1, y1, x2, y2, layer, width, uid):
    return ['\t(fp_rect',
            f'\t\t(start {x1:.2f} {y1:.2f})',
            f'\t\t(end {x2:.2f} {y2:.2f})',
            f'\t\t(stroke (width {width}) (type default))',
            '\t\t(fill no)',
            f'\t\t(layer "{layer}")',
            f'\t\t(uuid "{uid}")',
            '\t)']

# Module body, and a courtyard that also covers the overhanging horns.
for layer, width in (("F.SilkS", 0.12), ("F.Fab", 0.1)):
    out += rect(x_left, -BODY_W / 2, x_right, BODY_W / 2, layer, width, u())
out += rect(x_left - 0.25, -BODY_W / 2 - 0.25, x_right + HORN + 0.25,
            BODY_W / 2 + 0.25, "F.CrtYd", 0.05, u())

for i, name in enumerate(PADS):
    y = YS[i]
    shape = "rect" if i == 0 else "circle"     # pad 1 square = orientation key
    out += [f'\t(pad "{i+1}" thru_hole {shape}',
            f'\t\t(at 0 {y:.3f})',
            f'\t\t(size {PAD_D} {PAD_D})',
            f'\t\t(drill {DRILL_D})',
            '\t\t(layers "*.Cu" "*.Mask")',
            '\t\t(remove_unused_layers no)',
            f'\t\t(uuid "{u()}")',
            '\t)',
            f'\t(fp_text user "{name}"',
            f'\t\t(at -2.2 {y:.3f} 0)',
            '\t\t(layer "F.SilkS")',
            f'\t\t(uuid "{u()}")',
            '\t\t(effects (font (size 1.0 1.0) (thickness 0.15)) (justify right))',
            '\t)']

out.append(')')
open("epcal.pretty/TP4056_Module_03962A.kicad_mod", "w").write("\n".join(out) + "\n")
print(f"pads={len(PADS)}  span={SPAN:.3f}mm  gaps={'/'.join(f'{g:.3f}' for g in GAPS)}  body={BODY_L}x{BODY_W}mm")
print("  y: " + "  ".join(f"{n}={y:+.3f}" for n, y in zip(PADS, YS)))
