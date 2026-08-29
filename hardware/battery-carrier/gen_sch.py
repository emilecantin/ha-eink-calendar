#!/usr/bin/env python3
"""Generate the battery carrier schematic and project files.

Connectivity is expressed with global labels rather than drawn wires: for a
board this small it is unambiguous, and it keeps the generated schematic
readable and diffable.  Pin coordinates are read out of the real KiCad symbol
definitions rather than assumed, so labels land exactly on their pins.
"""
import os, re, uuid

GRID = 1.27          # KiCad's connection grid; pins off it trip ERC endpoint_off_grid
def snap(v):
    return round(round(v / GRID) * GRID, 4)

SYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = "battery-carrier"

def grab(libfile, name):
    """Pull one (symbol "NAME" ...) block out of a .kicad_sym by bracket matching."""
    src = open(libfile).read()
    m = re.search(r'\(symbol "%s"' % re.escape(name), src)
    assert m, f"{name} not in {libfile}"
    i, depth = m.start(), 0
    while True:
        if src[i] == '(': depth += 1
        elif src[i] == ')':
            depth -= 1
            if depth == 0: return src[m.start():i+1]
        i += 1

def pins(block):
    """Connection points of each pin: (number, x, y) in symbol coordinates."""
    out = []
    for pm in re.finditer(r'\(pin\s+\S+\s+\S+\s*\(at ([-\d.]+) ([-\d.]+) ([-\d.]+)\)', block):
        x, y = float(pm.group(1)), float(pm.group(2))
        nm = re.search(r'\(number "([^"]+)"', block[pm.end():pm.end()+400])
        out.append((nm.group(1) if nm else "?", x, y))
    return out

U1_SYM = '''(symbol "TP4056_Module"
    (pin_names (offset 1.016))
    (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "U" (at -7.62 11.43 0) (effects (font (size 1.27 1.27)) (justify left)))
    (property "Value" "TP4056_Module" (at -7.62 -13.97 0) (effects (font (size 1.27 1.27)) (justify left)))
    (property "Footprint" "epcal:TP4056_Module_03962A" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Description" "TP4056 Li-ion charger module with DW01A/FS8205A protection" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "TP4056_Module_0_1"
      (rectangle (start -7.62 10.16) (end 7.62 -12.7)
        (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "TP4056_Module_1_1"
      (pin power_out line (at 12.7 7.62 180) (length 5.08)
        (name "OUT+" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 12.7 2.54 180) (length 5.08)
        (name "B+" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 12.7 -2.54 180) (length 5.08)
        (name "B-" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin power_out line (at 12.7 -7.62 180) (length 5.08)
        (name "OUT-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    )
  )'''

open(f"{HERE}/epcal.kicad_sym", "w").write(
    '(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "epcal-gen")\n\t'
    + U1_SYM + '\n)\n')

# ref, lib_id, source lib file, symbol name, footprint, value, sheet x, y
PARTS = [
 ("U1","epcal:TP4056_Module",       None,               "TP4056_Module","epcal:TP4056_Module_03962A","TP4056 module", 60, 60),
 ("J1","Connector:Conn_01x02_Pin",  f"{SYM}/Connector.kicad_sym","Conn_01x02_Pin","Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical","18650", 110, 55),
 ("SW1","Switch:SW_SPST",           f"{SYM}/Switch.kicad_sym",   "SW_SPST","Button_Switch_THT:SW_DIP_SPSTx01_Slide_9.78x4.72mm_W7.62mm_P2.54mm","SPST", 110, 95),
 ("R1","Device:R",                  f"{SYM}/Device.kicad_sym",   "R","Resistor_SMD:R_0805_2012Metric","100k 1%", 150, 60),
 ("R2","Device:R",                  None,                        "R","Resistor_SMD:R_0805_2012Metric","100k 1%", 150, 85),
 ("C1","Device:C",                  f"{SYM}/Device.kicad_sym",   "C","Capacitor_SMD:C_0805_2012Metric","100nF", 175, 85),
 ("C3","Device:C",                  None,                        "C","Capacitor_SMD:C_0805_2012Metric","10uF", 200, 85),
 ("C2","Device:C_Polarized",        f"{SYM}/Device.kicad_sym",   "C_Polarized","Capacitor_SMD:CP_Elec_6.3x3.9","220uF 10V", 225, 85),
 ("J2","Connector:Conn_01x03_Pin",  f"{SYM}/Connector.kicad_sym","Conn_01x03_Pin","Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical","to ESP32", 110, 135),
 ("TP1","Connector:TestPoint",      f"{SYM}/Connector.kicad_sym","TestPoint","TestPoint:TestPoint_THTPad_1.5x1.5mm_Drill0.7mm","VSW", 250, 55),
 ("TP2","Connector:TestPoint",      None,                        "TestPoint","TestPoint:TestPoint_THTPad_1.5x1.5mm_Drill0.7mm","VSENSE", 265, 55),
]
NETS = {("U1","1"):"VOUT",("U1","2"):"BAT+",("U1","3"):"BAT-",("U1","4"):"GND",
        ("J1","1"):"BAT+",("J1","2"):"BAT-",("SW1","1"):"VOUT",("SW1","2"):"VSW",
        ("R1","2"):"VSW",("R1","1"):"VSENSE",("R2","2"):"VSENSE",("R2","1"):"GND",
        ("C1","2"):"VSENSE",("C1","1"):"GND",("C3","2"):"VSW",("C3","1"):"GND",
        ("C2","1"):"VSW",("C2","2"):"GND",
        ("J2","1"):"VSW",("J2","2"):"GND",("J2","3"):"VSENSE",
        ("TP1","1"):"VSW",("TP2","1"):"VSENSE"}

blocks, seen = [], {}
for ref, lib_id, libfile, name, fp, val, sx, sy in PARTS:
    if lib_id in seen: continue
    blk = U1_SYM if libfile is None and lib_id.startswith("epcal") else grab(libfile, name)
    seen[lib_id] = blk
    blocks.append('\t\t' + blk.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1))

sheet_uuid = str(uuid.uuid4())
S = ['(kicad_sch', '\t(version 20250114)', '\t(generator "epcal-gen")',
     '\t(generator_version "9.0")', f'\t(uuid "{sheet_uuid}")', '\t(paper "A4")',
     '\t(lib_symbols'] + blocks + ['\t)']

for ref, lib_id, libfile, name, fp, val, sx, sy in PARTS:
    sx, sy = snap(sx), snap(sy)      # keep every pin on the connection grid
    su = str(uuid.uuid4())
    bom = "no" if ref.startswith("TP") else "yes"   # match footprint attrs
    S += [f'\t(symbol', f'\t\t(lib_id "{lib_id}")', f'\t\t(at {sx} {sy} 0)',
          '\t\t(unit 1)', f'\t\t(exclude_from_sim no) (in_bom {bom}) (on_board yes) (dnp no)',
          f'\t\t(uuid "{su}")',
          f'\t\t(property "Reference" "{ref}" (at {sx} {sy-12} 0) (effects (font (size 1.27 1.27)) (justify left)))',
          f'\t\t(property "Value" "{val}" (at {sx} {sy+12} 0) (effects (font (size 1.27 1.27)) (justify left)))',
          f'\t\t(property "Footprint" "{fp}" (at {sx} {sy} 0) (effects (font (size 1.27 1.27)) hide))']
    for pn, px, py in pins(seen[lib_id]):
        S.append(f'\t\t(pin "{pn}" (uuid "{uuid.uuid4()}"))')
    S += ['\t\t(instances', f'\t\t\t(project "{PROJ}"',
          f'\t\t\t\t(path "/{sheet_uuid}" (reference "{ref}") (unit 1))', '\t\t\t)', '\t\t)', '\t)']
    # Global label on each pin's connection point (symbol Y is up-positive).
    for pn, px, py in pins(seen[lib_id]):
        net = NETS.get((ref, pn))
        if not net: continue
        lx, ly = sx + px, sy - py
        just = "left" if px >= 0 else "right"
        ang = 0 if px >= 0 else 180
        S += [f'\t(global_label "{net}"', '\t\t(shape bidirectional)',
              f'\t\t(at {lx} {ly} {ang})', '\t\t(fields_autoplaced yes)',
              f'\t\t(effects (font (size 1.27 1.27)) (justify {just}))',
              f'\t\t(uuid "{uuid.uuid4()}")', '\t)']

S += ['\t(sheet_instances', '\t\t(path "/" (page "1"))', '\t)', ')']
open(f"{HERE}/{PROJ}.kicad_sch", "w").write("\n".join(S) + "\n")

if not os.path.exists(f"{HERE}/{PROJ}.kicad_pro"):
    open(f"{HERE}/{PROJ}.kicad_pro", "w").write(
    '{\n  "board": {"design_settings": {}},\n  "meta": {"filename": "%s.kicad_pro", "version": 3},\n'
    '  "schematic": {},\n  "sheets": [["%s", "Root"]],\n  "text_variables": {}\n}\n' % (PROJ, sheet_uuid))
import shutil
print("lib tables preserved (see fp-lib-table / sym-lib-table)")
