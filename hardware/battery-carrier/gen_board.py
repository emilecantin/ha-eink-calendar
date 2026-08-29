#!/usr/bin/env python3
"""Generate the battery carrier PCB.

The TP4056 module lies flat over the left of the board and mates through its
four edge pads, so every other part sits to its right and nothing is trapped
underneath.  Flow runs left to right: cell in at J1 (sat midway between the
module's B+/B- pads, which the module spaces 7.6mm apart, so both battery tracks
stay short and neither crosses the other), through SW1, on to the divider and
the ESP32 connector.

VSW and VSENSE each get their own corridor -- VSW down the left at x=46, VSENSE
down the right at x=58 -- so the two never need to cross and the board stays
single-sided for signals, with a solid B.Cu ground pour underneath.
"""
import pcbnew, os, itertools

MM = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(MM(x), MM(y))

SS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
HERE = os.path.dirname(os.path.abspath(__file__))
BW, BH = 60.0, 30.0

board = pcbnew.CreateEmptyBoard()
nets = {}
for n in ("BAT+", "BAT-", "VOUT", "VSW", "VSENSE", "GND"):
    ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni

PARTS = [
 ("U1", f"{HERE}/epcal.pretty", "epcal:TP4056_Module_03962A",                       30.0, 15.0,   0, "TP4056 module"),
 ("J1", f"{SS}/Connector_JST.pretty","Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical",  37.5, 15.0, 270, "18650"),
 ("SW1",f"{SS}/Button_Switch_THT.pretty","Button_Switch_THT:SW_DIP_SPSTx01_Slide_9.78x4.72mm_W7.62mm_P2.54mm", 36.0, 4.0, 0, "SPST"),
 ("J2", f"{SS}/Connector_JST.pretty","Connector_JST:JST_PH_B3B-PH-K_1x03_P2.00mm_Vertical",  40.0, 26.0,   0, "to ESP32"),
 ("R1", f"{SS}/Resistor_SMD.pretty", "Resistor_SMD:R_0805_2012Metric",                      48.0,  8.0,  90, "100k 1%"),
 ("R2", f"{SS}/Resistor_SMD.pretty", "Resistor_SMD:R_0805_2012Metric",                      48.0, 12.0,  90, "100k 1%"),
 ("C3", f"{SS}/Capacitor_SMD.pretty","Capacitor_SMD:C_0805_2012Metric",                      52.0,  5.0,  90, "10uF"),
 ("C1", f"{SS}/Capacitor_SMD.pretty","Capacitor_SMD:C_0805_2012Metric",                      52.0, 10.0,  90, "100nF"),
 ("C2", f"{SS}/Capacitor_SMD.pretty","Capacitor_SMD:CP_Elec_6.3x3.9",                        52.0, 19.0,   0, "220uF 10V"),
 ("TP1",f"{SS}/TestPoint.pretty","TestPoint:TestPoint_THTPad_1.5x1.5mm_Drill0.7mm",      44.0,  8.5,   0, "VSW"),
 ("TP2",f"{SS}/TestPoint.pretty","TestPoint:TestPoint_THTPad_1.5x1.5mm_Drill0.7mm",      56.0, 25.0,   0, "VSENSE"),
 ("H1", f"{SS}/MountingHole.pretty","MountingHole:MountingHole_2.5mm_Pad_TopBottom",         3.0,  3.0,   0, ""),
 ("H2", f"{SS}/MountingHole.pretty","MountingHole:MountingHole_2.5mm_Pad_TopBottom",         3.0, 27.0,   0, ""),
]
fps = {}
for ref, lib, name, x, y, rot, val in PARTS:
    nick, _, bare = name.rpartition(":")
    fp = pcbnew.FootprintLoad(lib, bare); assert fp, name
    fp.SetFPID(pcbnew.LIB_ID(nick, bare))
    fp.SetReference(ref)
    fp.Value().SetVisible(False)
    if val: fp.SetValue(val)
    fp.SetPosition(V(x, y))
    if rot: fp.SetOrientationDegrees(rot)
    board.Add(fp); fps[ref] = fp

def pad(r, n):
    p = fps[r].FindPadByNumber(str(n)); assert p, f"{r}.{n}"; return p
def P(r, n):
    q = pad(r, n).GetPosition(); return (q.x / 1e6, q.y / 1e6)

# Fail loudly on overlapping courtyards rather than discovering it in DRC.
bad = []
for a, b in itertools.combinations([r for r in fps if r not in ("H1", "H2")], 2):
    ca = fps[a].GetCourtyard(pcbnew.F_CrtYd).BBox()
    cb = fps[b].GetCourtyard(pcbnew.F_CrtYd).BBox()
    if ca.Intersects(cb): bad.append((a, b))
if bad: raise SystemExit(f"courtyard overlap: {bad}")

for ref, (rx, ry) in {"SW1":(39.5,7.9), "TP1":(44.0,11.0), "TP2":(56.0,27.5),
                      "H1":(7.5,3.0), "H2":(7.5,27.0), "U1":(18.0,11.0),
                      "J1":(41.0,12.0), "J2":(36.0,22.0)}.items():
    fps[ref].Reference().SetPosition(V(rx, ry))
for ref in ("H1", "H2"):
    fps[ref].SetAttributes(fps[ref].GetAttributes() | pcbnew.FP_BOARD_ONLY
                           | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
for ref in ("TP1", "TP2"):
    fps[ref].SetAttributes(fps[ref].GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM
                           | pcbnew.FP_EXCLUDE_FROM_POS_FILES)

# Passives are rotated 90deg, which puts pad 1 at the BOTTOM. Assignments below
# follow that so the divider chain reads top-to-bottom VSW / VSENSE / GND and no
# track ever has to run across its own part.
CONN = [("U1",1,"VOUT"), ("U1",2,"BAT+"), ("U1",3,"BAT-"), ("U1",4,"GND"),
        ("J1",1,"BAT+"), ("J1",2,"BAT-"), ("SW1",1,"VOUT"), ("SW1",2,"VSW"),
        ("R1",2,"VSW"),  ("R1",1,"VSENSE"), ("R2",2,"VSENSE"), ("R2",1,"GND"),
        ("C1",2,"VSENSE"), ("C1",1,"GND"), ("C3",2,"VSW"), ("C3",1,"GND"),
        ("C2",1,"VSW"), ("C2",2,"GND"),
        ("J2",1,"VSW"), ("J2",2,"GND"), ("J2",3,"VSENSE"),
        ("TP1",1,"VSW"), ("TP2",1,"VSENSE")]
for r, n, net in CONN: pad(r, n).SetNet(nets[net])

for a, b in (((0,0),(BW,0)),((BW,0),(BW,BH)),((BW,BH),(0,BH)),((0,BH),(0,0))):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1)); board.Add(s)

def path(net, pts, w=0.5):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board); t.SetStart(V(*a)); t.SetEnd(V(*b))
        t.SetWidth(MM(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(nets[net]); board.Add(t)
def via(net, x, y):
    v = pcbnew.PCB_VIA(board); v.SetPosition(V(x, y))
    v.SetWidth(MM(0.8)); v.SetDrill(MM(0.4)); v.SetNet(nets[net]); board.Add(v)

path("BAT+", [P("U1",2), P("J1",1)], 0.8)
path("BAT-", [P("U1",3), P("J1",2)], 0.8)
path("VOUT", [P("U1",1), (34.3, 6.0), P("SW1",1)], 0.8)

path("VSW", [P("SW1",2), (46.0, 4.0), (46.0, 7.09), P("R1",2)], 0.5)
path("VSW", [(46.0, 4.0), P("C3",2)], 0.5)
path("VSW", [(46.0, 7.09), P("TP1",1)], 0.5)
path("VSW", [(46.0, 7.09), (46.0, 19.0), P("C2",1)], 0.8)
path("VSW", [(46.0, 19.0), (46.0, 23.1), (40.0, 23.1), P("J2",1)], 0.8)

path("VSENSE", [P("R1",1), P("R2",2)], 0.3)
path("VSENSE", [P("R1",1), (50.0, 9.09), P("C1",2)], 0.3)
path("VSENSE", [P("C1",2), (58.0, 9.09), (58.0, 24.0), P("TP2",1)], 0.3)
path("VSENSE", [P("TP2",1), P("J2",3)], 0.3)

# SMD ground pads need a via down to the pour; THT pads already reach it.
# Each via is placed away from the part's other pad so no track crosses it.
for r, n, vx, vy in (("R2",1,50.0,13.5), ("C1",1,52.0,12.8),
                     ("C3",1,52.0,7.3),  ("C2",2,53.5,23.4)):
    path("GND", [P(r,n), (vx,vy)], 0.5); via("GND", vx, vy)

zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.B_Cu); zone.SetNet(nets["GND"]); zone.SetLocalClearance(MM(0.3))
o = zone.Outline(); o.NewOutline()
for x, y in ((0.4,0.4),(BW-0.4,0.4),(BW-0.4,BH-0.4),(0.4,BH-0.4)): o.Append(MM(x), MM(y))
board.Add(zone)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

board.Save(f"{HERE}/battery-carrier.kicad_pcb")
print("saved, courtyards clear")
