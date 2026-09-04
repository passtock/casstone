import FreeCAD
import FreeCADGui
import Part
from FreeCAD import Base
import math
import os
import shutil

doc_name = "Finger_Keyboard_10Key_v2"

try:
    FreeCAD.closeDocument(doc_name)
except Exception:
    pass

doc = FreeCAD.newDocument(doc_name)

# -------------------------------------------------------------
# Dimensions (mm) - Heavy-Duty Reinforced Compact Edition
# -------------------------------------------------------------
W = 320.0        # Width (X)
D = 180.0        # Depth (Y)
H = 54.0         # Height (Z)
wall = 6.0       # Ultra-solid 6.0mm outer wall
top_t = 6.0      # Massive 6.0mm top plate with button latch relief pockets
base_t = 6.0     # Solid 6.0mm base plate
btn_latch_t = 3.5# Snap-in button latch thickness (2.5mm relief from underside)
R_corner = 8.0   # Corner Fillet Radius

# -------------------------------------------------------------
# 1. Main Upper Housing Outer Box
# -------------------------------------------------------------
outer_box = Part.makeBox(W, D, H)

# Fillet 4 vertical corner edges
vert_edges = []
for e in outer_box.Edges:
    v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
    if abs(v1.x - v2.x) < 0.01 and abs(v1.y - v2.y) < 0.01 and abs(v1.z - v2.z) > 1.0:
        vert_edges.append(e)

if len(vert_edges) == 4:
    outer_shell = outer_box.makeFillet(R_corner, vert_edges)
else:
    outer_shell = outer_box

# Inner cavity
inner_w = W - 2 * wall
inner_d = D - 2 * wall
inner_h = H - top_t
inner_box = Part.makeBox(inner_w, inner_d, inner_h, Base.Vector(wall, wall, 0.0))

inner_vert_edges = []
for e in inner_box.Edges:
    v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
    if abs(v1.x - v2.x) < 0.01 and abs(v1.y - v2.y) < 0.01 and abs(v1.z - v2.z) > 1.0:
        inner_vert_edges.append(e)

if len(inner_vert_edges) == 4:
    inner_cavity = inner_box.makeFillet(max(1.0, R_corner - wall), inner_vert_edges)
else:
    inner_cavity = inner_box

hollow_housing = outer_shell.cut(inner_cavity)

# -------------------------------------------------------------
# 2. 10 Button Holes (30.0 mm dia) + Underside Relief Pockets (38.0 mm dia)
# -------------------------------------------------------------
# Layout (W=320, D=180, Center X=160)
buttons_layout = [
    # Left Hand (Pinky, Ring, Middle, Index, Thumb)
    ("L_Pinky",  32.0,  95.0),
    ("L_Ring",   66.0,  118.0),
    ("L_Middle", 102.0, 130.0),
    ("L_Index",  138.0, 114.0),
    ("L_Thumb",  112.0,  56.0),
    # Right Hand (Index, Middle, Ring, Pinky, Thumb)
    ("R_Index",  182.0, 114.0),
    ("R_Middle", 218.0, 130.0),
    ("R_Ring",   254.0, 118.0),
    ("R_Pinky",  288.0,  95.0),
    ("R_Thumb",  208.0,  56.0),
]

btn_hole_r = 15.0     # 30.0 mm diameter through-hole
relief_r = 19.5       # 39.0 mm diameter relief pocket from underside
relief_depth = top_t - btn_latch_t # 2.5 mm deep pocket from underneath

housing_with_btns = hollow_housing

for name, bx, by in buttons_layout:
    # 1. Through hole (cuts entire 6.0mm top plate)
    th_hole = Part.makeCylinder(btn_hole_r, top_t + 4.0, Base.Vector(bx, by, H - top_t - 2.0), Base.Vector(0, 0, 1))
    housing_with_btns = housing_with_btns.cut(th_hole)
    
    # 2. Underside latch relief pocket (leaving 3.5mm flange for snap-in wings)
    relief_pocket = Part.makeCylinder(relief_r, relief_depth + 0.1, Base.Vector(bx, by, H - top_t - 0.05), Base.Vector(0, 0, 1))
    housing_with_btns = housing_with_btns.cut(relief_pocket)

# -------------------------------------------------------------
# 3. Rear GX16 Aviation Connector Holes (3 x 16.0 mm dia)
# -------------------------------------------------------------
jack_hole_r = 8.0     # 16.0 mm diameter
jack_z = H / 2.0      # 27.0 mm center height
jack_x_positions = [80.0, 160.0, 240.0]

housing_with_ports = housing_with_btns
for jx in jack_x_positions:
    cutter = Part.makeCylinder(jack_hole_r, wall + 6.0, Base.Vector(jx, D - wall - 3.0, jack_z), Base.Vector(0, 1, 0))
    housing_with_ports = housing_with_ports.cut(cutter)

# -------------------------------------------------------------
# 4. Waterproof Tongue/Lip on Upper Shell Bottom Edge
# -------------------------------------------------------------
# Lip dimensions: width 2.0mm, height 1.8mm protruding from bottom perimeter
lip_offset = wall / 2.0 # center of 6.0mm wall (3.0mm from edge)
lip_w = W - 2 * (wall - 2.0)
lip_d = D - 2 * (wall - 2.0)
lip_h = 1.8

lip_outer = Part.makeBox(W - 4.0, D - 4.0, lip_h, Base.Vector(2.0, 2.0, -lip_h))
lip_inner = Part.makeBox(W - 8.0, D - 8.0, lip_h + 1.0, Base.Vector(4.0, 4.0, -lip_h - 0.5))
sealing_lip = lip_outer.cut(lip_inner)

housing_with_lip = housing_with_ports.fuse(sealing_lip)

# -------------------------------------------------------------
# 5. Fastener Bosses (6 Standoff Pillars for M3 Threaded Inserts)
# -------------------------------------------------------------
boss_outer_r = 5.0     # 10.0 mm diameter heavy-duty boss
boss_insert_r = 2.0    # 4.0 mm hole for standard M3 heat-set insert (M3x4.6x5.7)
boss_h = H - top_t
corner_offset = 14.0

boss_positions = [
    (corner_offset, corner_offset),            # Front-Left
    (W - corner_offset, corner_offset),        # Front-Right
    (corner_offset, D - corner_offset),        # Rear-Left
    (W - corner_offset, D - corner_offset),    # Rear-Right
    (W / 2.0, corner_offset),                  # Front-Center
    (W / 2.0, D - corner_offset),              # Rear-Center
]

final_housing = housing_with_lip
for cx, cy in boss_positions:
    outer_cyl = Part.makeCylinder(boss_outer_r, boss_h, Base.Vector(cx, cy, 0.0), Base.Vector(0, 0, 1))
    inner_cyl = Part.makeCylinder(boss_insert_r, 8.0, Base.Vector(cx, cy, 0.0), Base.Vector(0, 0, 1))
    b = outer_cyl.cut(inner_cyl)
    final_housing = final_housing.fuse(b)

housing_obj = doc.addObject("Part::Feature", "UpperHousing_HD")
housing_obj.Shape = final_housing
housing_obj.ViewObject.ShapeColor = (0.2, 0.22, 0.26, 1.0) # Matte Tactical Dark Grey

# -------------------------------------------------------------
# 6. Heavy-Duty Bottom Base Plate (6.0mm thickness) + Gasket Groove + M3 Counterbores
# -------------------------------------------------------------
base_raw = Part.makeBox(W, D, base_t, Base.Vector(0.0, 0.0, -base_t - lip_h))

# Corner fillet on base
base_vert_edges = []
for e in base_raw.Edges:
    v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
    if abs(v1.x - v2.x) < 0.01 and abs(v1.y - v2.y) < 0.01 and abs(v1.z - v2.z) > 1.0:
        base_vert_edges.append(e)

if len(base_vert_edges) == 4:
    base_filleted = base_raw.makeFillet(R_corner, base_vert_edges)
else:
    base_filleted = base_raw

# Perimeter Gasket / O-ring Channel (Width 3.0mm, Depth 2.5mm)
groove_outer = Part.makeBox(W - 3.5, D - 3.5, 2.5, Base.Vector(1.75, 1.75, -lip_h - 2.5))
groove_inner = Part.makeBox(W - 9.5, D - 9.5, 3.0, Base.Vector(4.75, 4.75, -lip_h - 2.7))
gasket_groove = groove_outer.cut(groove_inner)

base_with_groove = base_filleted.cut(gasket_groove)

# 6 x M3 Counterbore Screw Holes in Base
# ISO 4762 M3: Through-hole 3.4mm, Counterbore dia 6.5mm, depth 3.5mm
base_with_screws = base_with_groove
for cx, cy in boss_positions:
    # 3.4mm through-hole
    th = Part.makeCylinder(1.7, base_t + 2.0, Base.Vector(cx, cy, -base_t - lip_h - 1.0), Base.Vector(0, 0, 1))
    # 6.5mm counterbore from the bottom face
    cb = Part.makeCylinder(3.25, 3.5, Base.Vector(cx, cy, -base_t - lip_h - 0.1), Base.Vector(0, 0, 1))
    base_with_screws = base_with_screws.cut(th).cut(cb)

# 4 Rubber Feet Recesses (dia 14mm, depth 1.5mm) in corners
foot_r = 7.0
foot_depth = 1.5
foot_positions = [
    (28.0, 28.0),
    (W - 28.0, 28.0),
    (28.0, D - 28.0),
    (W - 28.0, D - 28.0)
]
for fx, fy in foot_positions:
    f_pocket = Part.makeCylinder(foot_r, foot_depth + 0.1, Base.Vector(fx, fy, -base_t - lip_h - 0.1), Base.Vector(0, 0, 1))
    base_with_screws = base_with_screws.cut(f_pocket)

base_obj = doc.addObject("Part::Feature", "BottomBasePlate_HD")
base_obj.Shape = base_with_screws
base_obj.ViewObject.ShapeColor = (0.13, 0.14, 0.16, 1.0) # Deep Charcoal

# -------------------------------------------------------------
# 7. Virtual 3D Arcade Buttons & Metal Connectors (for render visualization)
# -------------------------------------------------------------
rim_r = 33.5 / 2.0
cap_r = 25.0 / 2.0
rim_h = 3.0
cap_h = 3.5

for name, bx, by in buttons_layout:
    # Black Rim Flange
    rim = Part.makeCylinder(rim_r, rim_h, Base.Vector(bx, by, H), Base.Vector(0, 0, 1))
    rim_obj = doc.addObject("Part::Feature", f"{name}_Rim")
    rim_obj.Shape = rim
    rim_obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1, 1.0)
    
    # Bright Green Button Plunger
    cap = Part.makeCylinder(cap_r, cap_h, Base.Vector(bx, by, H + rim_h), Base.Vector(0, 0, 1))
    cap_obj = doc.addObject("Part::Feature", f"{name}_Cap")
    cap_obj.Shape = cap
    cap_obj.ViewObject.ShapeColor = (0.1, 0.85, 0.25, 1.0)

for idx, jx in enumerate(jack_x_positions, 1):
    collar = Part.makeCylinder(9.5, 4.5, Base.Vector(jx, D, jack_z), Base.Vector(0, 1, 0))
    jack_obj = doc.addObject("Part::Feature", f"GX16_Jack_{idx}")
    jack_obj.Shape = collar
    jack_obj.ViewObject.ShapeColor = (0.78, 0.80, 0.84, 1.0)

doc.recompute()

# -------------------------------------------------------------
# 8. Export Files directly to: C:\Users\passp\OneDrive\바탕 화면\jeayong\머신\01_컨트롤러_3D도면_CAD
# -------------------------------------------------------------
export_dir = r"c:\Users\passp\OneDrive\바탕 화면\jeayong\머신\01_컨트롤러_3D도면_CAD"
os.makedirs(export_dir, exist_ok=True)

fcstd_path = os.path.join(export_dir, "Finger_Keyboard_10Key_Reinforced.FCStd")
doc.saveAs(fcstd_path)

step_path = os.path.join(export_dir, "Finger_Keyboard_Housing_Reinforced.step")
Part.export([housing_obj, base_obj], step_path)

stl_housing_path = os.path.join(export_dir, "Finger_Keyboard_Housing_Reinforced.stl")
Part.export([housing_obj], stl_housing_path)

stl_base_path = os.path.join(export_dir, "Finger_Keyboard_Base_Reinforced.stl")
Part.export([base_obj], stl_base_path)

# Also save this generator script in the target folder
shutil.copy2(r"C:\Users\passp\.gemini\antigravity-ide\brain\1be60f37-311a-4eb3-9b24-b78b2f947137\scratch\generate_enclosure_v2.py",
             os.path.join(export_dir, "generate_enclosure_reinforced.py"))

print("REINFORCED 3D CAD MODELING & EXPORT COMPLETE!")
print("Saved FCStd:", fcstd_path)
print("Exported STEP:", step_path)
print("Exported STL (Housing):", stl_housing_path)
print("Exported STL (Base):", stl_base_path)
