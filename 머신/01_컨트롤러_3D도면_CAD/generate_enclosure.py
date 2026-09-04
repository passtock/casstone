import FreeCAD
import FreeCADGui
import Part
from FreeCAD import Base
import math
import os

doc_name = "Finger_Keyboard_10Key"

try:
    FreeCAD.closeDocument(doc_name)
except Exception:
    pass

doc = FreeCAD.newDocument(doc_name)

# -------------------------------------------------------------
# Dimensions (mm)
# -------------------------------------------------------------
W = 360.0      # Width (X)
D = 210.0      # Depth (Y)
H = 52.0       # Total Height (Z)
wall = 3.5     # Outer Wall Thickness
top_t = 3.0    # Top Mounting Plate Thickness (optimal for 30mm snap-in clips)
base_t = 3.0   # Bottom Base Plate Thickness
R_corner = 8.0 # Corner Fillet Radius

# -------------------------------------------------------------
# 1. Main Upper Housing (Outer Box)
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

# Inner hollow cavity (open at bottom Z=0)
inner_w = W - 2 * wall
inner_d = D - 2 * wall
inner_h = H - top_t
inner_box = Part.makeBox(inner_w, inner_d, inner_h, Base.Vector(wall, wall, 0.0))

# Fillet inner vertical edges
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
# 2. 10 Ergonomic Button Holes (Diameter 30.0 mm)
# -------------------------------------------------------------
buttons_layout = [
    # Left Hand (Pinky, Ring, Middle, Index, Thumb)
    ("L_Pinky",  38.0,  115.0),
    ("L_Ring",   74.0,  138.0),
    ("L_Middle", 110.0, 148.0),
    ("L_Index",  146.0, 130.0),
    ("L_Thumb",  120.0,  70.0),
    # Right Hand (Index, Middle, Ring, Pinky, Thumb)
    ("R_Index",  214.0, 130.0),
    ("R_Middle", 250.0, 148.0),
    ("R_Ring",   286.0, 138.0),
    ("R_Pinky",  322.0, 115.0),
    ("R_Thumb",  240.0,  70.0),
]

btn_hole_r = 15.0  # Diameter 30.0 mm
btn_holes = []
for name, bx, by in buttons_layout:
    hole = Part.makeCylinder(btn_hole_r, top_t + 6.0, Base.Vector(bx, by, H - top_t - 3.0), Base.Vector(0, 0, 1))
    btn_holes.append(hole)

# Cut button holes from housing
housing_with_btn_holes = hollow_housing
for h in btn_holes:
    housing_with_btn_holes = housing_with_btn_holes.cut(h)

# -------------------------------------------------------------
# 3. Rear Aviation Connector Holes (3 x GX16, Diameter 16.0 mm)
# -------------------------------------------------------------
# Rear wall is at Y = D (210 mm)
jack_hole_r = 8.0   # Diameter 16.0 mm (GX16)
jack_z = H / 2.0    # Z = 26.0 mm (center height)
jack_x_positions = [100.0, 180.0, 260.0]

jack_cutters = []
for jx in jack_x_positions:
    # Cylinder oriented along Y axis: direction Vector(0, 1, 0)
    cutter = Part.makeCylinder(jack_hole_r, wall + 6.0, Base.Vector(jx, D - wall - 3.0, jack_z), Base.Vector(0, 1, 0))
    jack_cutters.append(cutter)

housing_with_ports = housing_with_btn_holes
for jc in jack_cutters:
    housing_with_ports = housing_with_ports.cut(jc)

# -------------------------------------------------------------
# 4. Corner Standoff Bosses (Screw mounting posts)
# -------------------------------------------------------------
boss_outer_r = 4.5
boss_inner_r = 1.6  # for M3 screw
boss_h = H - top_t
corner_margin = 15.0
boss_positions = [
    (corner_margin, corner_margin),
    (W - corner_margin, corner_margin),
    (corner_margin, D - corner_margin),
    (W - corner_margin, D - corner_margin)
]

bosses = []
for cx, cy in boss_positions:
    outer_cyl = Part.makeCylinder(boss_outer_r, boss_h, Base.Vector(cx, cy, 0.0), Base.Vector(0, 0, 1))
    inner_hole = Part.makeCylinder(boss_inner_r, boss_h + 1.0, Base.Vector(cx, cy, 0.0), Base.Vector(0, 0, 1))
    boss = outer_cyl.cut(inner_hole)
    bosses.append(boss)

final_housing_shape = housing_with_ports
for b in bosses:
    final_housing_shape = final_housing_shape.fuse(b)

housing_obj = doc.addObject("Part::Feature", "UpperHousing")
housing_obj.Shape = final_housing_shape
housing_obj.ViewObject.ShapeColor = (0.22, 0.24, 0.28, 1.0) # Sleek Dark Matte Grey
housing_obj.ViewObject.Transparency = 0

# -------------------------------------------------------------
# 5. Bottom Base Plate
# -------------------------------------------------------------
base_raw = Part.makeBox(W, D, base_t, Base.Vector(0.0, 0.0, -base_t - 0.5))
base_vert_edges = []
for e in base_raw.Edges:
    v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
    if abs(v1.x - v2.x) < 0.01 and abs(v1.y - v2.y) < 0.01 and abs(v1.z - v2.z) > 0.5:
        base_vert_edges.append(e)

if len(base_vert_edges) == 4:
    base_filleted = base_raw.makeFillet(R_corner, base_vert_edges)
else:
    base_filleted = base_raw

# Screw through-holes in base plate
base_holes = []
for cx, cy in boss_positions:
    sh = Part.makeCylinder(1.7, base_t + 2.0, Base.Vector(cx, cy, -base_t - 1.5), Base.Vector(0, 0, 1))
    base_holes.append(sh)

final_base_shape = base_filleted
for sh in base_holes:
    final_base_shape = final_base_shape.cut(sh)

base_obj = doc.addObject("Part::Feature", "BottomBasePlate")
base_obj.Shape = final_base_shape
base_obj.ViewObject.ShapeColor = (0.15, 0.16, 0.18, 1.0) # Dark Charcoal Base

# -------------------------------------------------------------
# 6. Photorealistic Virtual 3D Buttons (for visualization)
# -------------------------------------------------------------
rim_r = 33.5 / 2.0
cap_r = 25.0 / 2.0
rim_h = 3.0
cap_h = 3.5

for name, bx, by in buttons_layout:
    # Outer Rim (Black flange)
    rim = Part.makeCylinder(rim_r, rim_h, Base.Vector(bx, by, H), Base.Vector(0, 0, 1))
    rim_obj = doc.addObject("Part::Feature", f"{name}_Rim")
    rim_obj.Shape = rim
    rim_obj.ViewObject.ShapeColor = (0.12, 0.12, 0.12, 1.0)
    
    # Plunger Cap (Vibrant Arcade Green)
    cap = Part.makeCylinder(cap_r, cap_h, Base.Vector(bx, by, H + rim_h), Base.Vector(0, 0, 1))
    cap_obj = doc.addObject("Part::Feature", f"{name}_Cap")
    cap_obj.Shape = cap
    cap_obj.ViewObject.ShapeColor = (0.1, 0.85, 0.25, 1.0) # Vivid Green button

# -------------------------------------------------------------
# 7. Virtual Aviation Jacks (GX16 Connectors for visualization)
# -------------------------------------------------------------
for idx, jx in enumerate(jack_x_positions, 1):
    # Metal collar flange
    collar = Part.makeCylinder(9.5, 4.0, Base.Vector(jx, D, jack_z), Base.Vector(0, 1, 0))
    jack_obj = doc.addObject("Part::Feature", f"GX16_Jack_{idx}")
    jack_obj.Shape = collar
    jack_obj.ViewObject.ShapeColor = (0.75, 0.78, 0.82, 1.0) # Metallic Silver

doc.recompute()

# -------------------------------------------------------------
# 8. Export Files (FCStd, STEP, STL)
# -------------------------------------------------------------
export_dir = r"c:\Users\passp\OneDrive\바탕 화면\jeayong\capstone\06_컨트롤러_3D도면_CAD"
os.makedirs(export_dir, exist_ok=True)

fcstd_path = os.path.join(export_dir, "Finger_Keyboard_10Key.FCStd")
doc.saveAs(fcstd_path)

step_path = os.path.join(export_dir, "Finger_Keyboard_Housing.step")
Part.export([housing_obj, base_obj], step_path)

stl_housing_path = os.path.join(export_dir, "Finger_Keyboard_Housing.stl")
Part.export([housing_obj], stl_housing_path)

stl_base_path = os.path.join(export_dir, "Finger_Keyboard_Base.stl")
Part.export([base_obj], stl_base_path)

print("SUCCESS: 3D CAD modeling and file exports complete!")
print("Saved FCStd:", fcstd_path)
print("Exported STEP:", step_path)
print("Exported STL (Housing):", stl_housing_path)
print("Exported STL (Base):", stl_base_path)
