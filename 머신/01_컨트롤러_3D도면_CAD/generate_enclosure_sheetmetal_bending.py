import FreeCAD
import Part
from FreeCAD import Base
import math
import os

doc_name = "Finger_Keyboard_SheetMetal_Bending"

try:
    FreeCAD.closeDocument(doc_name)
except Exception:
    pass

doc = FreeCAD.newDocument(doc_name)

def set_color(obj, color):
    try:
        if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
            obj.ViewObject.ShapeColor = color
    except Exception:
        pass

# -------------------------------------------------------------
# Dimensions (mm) - Zero-Weld 2-Piece Bending Sheet Metal Enclosure
# -------------------------------------------------------------
W = 320.0        # Total Width (X)
D = 180.0        # Total Depth (Y)
H = 50.0         # Total Enclosure Height (Z)
t = 2.0          # 2.0t Steel / Sheet Metal Thickness
flange_w = 14.0  # Bottom return mounting flange width
gap = 0.3        # Laser cutting tolerance gap between parts

# -------------------------------------------------------------
# 1. Part 1: Top Cover (상부 ㄷ자 커버: 상판 + 전면벽 + 후면벽 + 하단안착플랜지)
# -------------------------------------------------------------
# Top face: X from 0 to W, Y from 0 to D, Z from H - t to H
top_plate = Part.makeBox(W, D, t, Base.Vector(0, 0, H - t))

# Front wall: X from 0 to W, Y from 0 to t, Z from t to H - t
front_wall = Part.makeBox(W, t, H - 2 * t, Base.Vector(0, 0, t))

# Rear wall: X from 0 to W, Y from D - t to D, Z from t to H - t
rear_wall = Part.makeBox(W, t, H - 2 * t, Base.Vector(0, D - t, t))

# Front bottom return lip: X from 10 to W - 10, Y from t to t + flange_w, Z from t to 2 * t
front_lip = Part.makeBox(W - 20.0, flange_w, t, Base.Vector(10.0, t, t))

# Rear bottom return lip (with a 70mm center notch for GX16 cable clearance):
# Left segment: X from 10 to 125, Y from D - t - flange_w to D - t, Z from t to 2 * t
rear_lip_left = Part.makeBox(115.0, flange_w, t, Base.Vector(10.0, D - t - flange_w, t))
# Right segment: X from 195 to W - 10, Y from D - t - flange_w to D - t, Z from t to 2 * t
rear_lip_right = Part.makeBox(115.0, flange_w, t, Base.Vector(195.0, D - t - flange_w, t))

cover_solid = top_plate.fuse(front_wall).fuse(rear_wall).fuse(front_lip).fuse(rear_lip_left).fuse(rear_lip_right)

# -------------------------------------------------------------
# 2. Press Brake Bend Fillets on Top Cover (Front & Rear Top Edges)
# -------------------------------------------------------------
# In sheet metal, outer bend radius is ~3.5-4.0mm (smooth and safe for hands)
cover_filleted = cover_solid
bend_edges = []
for e in cover_solid.Edges:
    v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
    # Top front outer edge: Y ≈ 0, Z ≈ H
    if abs(v1.y) < 0.01 and abs(v2.y) < 0.01 and abs(v1.z - H) < 0.01 and abs(v2.z - H) < 0.01:
        bend_edges.append(e)
    # Top rear outer edge: Y ≈ D, Z ≈ H
    if abs(v1.y - D) < 0.01 and abs(v2.y - D) < 0.01 and abs(v1.z - H) < 0.01 and abs(v2.z - H) < 0.01:
        bend_edges.append(e)

if len(bend_edges) == 2:
    try:
        cover_filleted = cover_solid.makeFillet(3.5, bend_edges)
    except Exception:
        cover_filleted = cover_solid

# -------------------------------------------------------------
# 3. 10 Ergonomic 30.0mm Button Holes on Top Plate
# -------------------------------------------------------------
buttons_layout = [
    # Left Hand (Pinky, Ring, Middle, Index, Thumb)
    ("L_Pinky",  32.0,  95.0),
    ("L_Ring",   66.0,  118.0),
    ("L_Middle", 102.0, 130.0),
    ("L_Index",  138.0, 114.0),
    ("L_Thumb",  112.0,  56.0),
    # Right Hand (Index, Middle, Ring, Pinky, Thumb) - Symmetric across X=160
    ("R_Index",  182.0, 114.0),
    ("R_Middle", 218.0, 130.0),
    ("R_Ring",   254.0, 118.0),
    ("R_Pinky",  288.0,  95.0),
    ("R_Thumb",  208.0,  56.0),
]

btn_hole_r = 15.0 # 30.0 mm diameter for 29.5φ snap-in arcade buttons
cover_with_btns = cover_filleted
for name, bx, by in buttons_layout:
    h = Part.makeCylinder(btn_hole_r, t + 4.0, Base.Vector(bx, by, H - t - 2.0), Base.Vector(0, 0, 1))
    cover_with_btns = cover_with_btns.cut(h)

# -------------------------------------------------------------
# 4. Rear GX16 Aviation Connector Holes (3 x 16.0 mm dia)
# -------------------------------------------------------------
jack_hole_r = 8.0  # 16.0 mm diameter
jack_z = 25.0      # Center height Z = 25.0 mm
jack_x_positions = [80.0, 160.0, 240.0]

cover_with_ports = cover_with_btns
for jx in jack_x_positions:
    cutter = Part.makeCylinder(jack_hole_r, t + 4.0, Base.Vector(jx, D - t - 2.0, jack_z), Base.Vector(0, 1, 0))
    cover_with_ports = cover_with_ports.cut(cutter)

# -------------------------------------------------------------
# 5. Mounting Screw Holes on Bottom Lips of Top Cover (5 x M4 Tapped/Weld Nut Holes)
# -------------------------------------------------------------
screw_positions = [
    (60.0,  t + flange_w / 2.0),            # Front-Left
    (160.0, t + flange_w / 2.0),            # Front-Center
    (260.0, t + flange_w / 2.0),            # Front-Right
    (60.0,  D - t - flange_w / 2.0),        # Rear-Left
    (260.0, D - t - flange_w / 2.0),        # Rear-Right
    # Rear-Center is open (0 collision with middle GX16 jack)
]

cover_with_screws = cover_with_ports
for sx, sy in screw_positions:
    # 3.3 mm pilot hole for M4 tapping (standard M4 coarse thread pitch 0.7mm)
    sh = Part.makeCylinder(1.65, t + 2.0, Base.Vector(sx, sy, t - 1.0), Base.Vector(0, 0, 1))
    cover_with_screws = cover_with_screws.cut(sh)

top_cover_obj = doc.addObject("Part::Feature", "SheetMetal_TopCover")
top_cover_obj.Shape = cover_with_screws
set_color(top_cover_obj, (0.30, 0.33, 0.38, 1.0)) # Gunmetal Fine Powdercoat Finish

# -------------------------------------------------------------
# 6. Part 2: Bottom Chassis (하부 ㄷ자 베이스: 바닥판 + 좌측벽 + 우측벽 + 상단보강플랜지)
# -------------------------------------------------------------
# Bottom plate covers the entire bottom: X from 0 to W, Y from 0 to D, Z from 0 to t
bot_base = Part.makeBox(W, D, t, Base.Vector(0, 0, 0))

# Left Wall: rises from Z = t to H - t - gap, inside front/rear walls (Y from t + gap to D - t - gap)
left_wall_d = D - 2 * (t + gap)
left_wall_h = H - 2 * t - gap
left_wall = Part.makeBox(t, left_wall_d, left_wall_h, Base.Vector(t + gap, t + gap, t))

# Right Wall:
right_wall = Part.makeBox(t, left_wall_d, left_wall_h, Base.Vector(W - 2 * t - gap, t + gap, t))

# Top inward return lips on left & right walls (gives huge longitudinal bending stiffness):
left_top_lip = Part.makeBox(12.0, left_wall_d, t, Base.Vector(t + gap, t + gap, H - 2 * t - gap))
right_top_lip = Part.makeBox(12.0, left_wall_d, t, Base.Vector(W - 2 * t - gap - 12.0, t + gap, H - 2 * t - gap))

chassis_solid = bot_base.fuse(left_wall).fuse(right_wall).fuse(left_top_lip).fuse(right_top_lip)

# 5 x M4 Countersunk Screw Holes on the Bottom Base Plate (matching top cover bottom lips)
# DIN 7991 M4: Through-hole 4.5mm, Countersink 90° to dia 8.4mm
chassis_with_screws = chassis_solid
for sx, sy in screw_positions:
    th = Part.makeCylinder(2.25, t + 2.0, Base.Vector(sx, sy, -1.0), Base.Vector(0, 0, 1))
    cs = Part.makeCone(4.2, 2.25, t, Base.Vector(sx, sy, 0), Base.Vector(0, 0, 1))
    chassis_with_screws = chassis_with_screws.cut(th).cut(cs)

# 4 Rubber Feet Recesses / Mounts in Corners
foot_positions = [
    (25.0, 25.0),
    (W - 25.0, 25.0),
    (25.0, D - 25.0),
    (W - 25.0, D - 25.0)
]
for fx, fy in foot_positions:
    fp = Part.makeCylinder(6.0, 0.8, Base.Vector(fx, fy, -0.1), Base.Vector(0, 0, 1))
    chassis_with_screws = chassis_with_screws.cut(fp)

bottom_base_obj = doc.addObject("Part::Feature", "SheetMetal_BottomChassis")
bottom_base_obj.Shape = chassis_with_screws
set_color(bottom_base_obj, (0.18, 0.20, 0.22, 1.0)) # Matte Anodized Dark Charcoal

# -------------------------------------------------------------
# 7. Virtual Arcade Buttons & Aviation Connectors (for render visualization)
# -------------------------------------------------------------
rim_r = 33.5 / 2.0
cap_r = 25.0 / 2.0
rim_h = 3.0
cap_h = 3.5

for name, bx, by in buttons_layout:
    rim = Part.makeCylinder(rim_r, rim_h, Base.Vector(bx, by, H), Base.Vector(0, 0, 1))
    rim_obj = doc.addObject("Part::Feature", f"{name}_Rim")
    rim_obj.Shape = rim
    set_color(rim_obj, (0.1, 0.1, 0.1, 1.0))
    
    cap = Part.makeCylinder(cap_r, cap_h, Base.Vector(bx, by, H + rim_h), Base.Vector(0, 0, 1))
    cap_obj = doc.addObject("Part::Feature", f"{name}_Cap")
    cap_obj.Shape = cap
    set_color(cap_obj, (0.1, 0.85, 0.25, 1.0))

for idx, jx in enumerate(jack_x_positions, 1):
    collar = Part.makeCylinder(9.5, 4.5, Base.Vector(jx, D, jack_z), Base.Vector(0, 1, 0))
    jack_obj = doc.addObject("Part::Feature", f"GX16_Jack_{idx}")
    jack_obj.Shape = collar
    set_color(jack_obj, (0.78, 0.80, 0.84, 1.0))

doc.recompute()

# -------------------------------------------------------------
# 8. Export Files (FCStd, Individual STEPs, Assembly STEP, STLs)
# -------------------------------------------------------------
export_dir = r"c:\Users\passp\OneDrive\바탕 화면\jeayong\머신\01_컨트롤러_3D도면_CAD"
os.makedirs(export_dir, exist_ok=True)

# 1. FreeCAD Project Native Document
fcstd_path = os.path.join(export_dir, "Finger_Keyboard_SheetMetal_Bending.FCStd")
doc.saveAs(fcstd_path)

# 2. STEP Files (Industry standard CAD files for laser cutting and CNC bending)
step_housing_path = os.path.join(export_dir, "Finger_Keyboard_TopCover_Bending.step")
Part.export([top_cover_obj], step_housing_path)

step_base_path = os.path.join(export_dir, "Finger_Keyboard_BottomBase_Bending.step")
Part.export([bottom_base_obj], step_base_path)

step_assembly_path = os.path.join(export_dir, "Finger_Keyboard_Assembly_Bending.step")
Part.export([top_cover_obj, bottom_base_obj], step_assembly_path)

# 3. STL Files
stl_housing_path = os.path.join(export_dir, "Finger_Keyboard_TopCover_Bending.stl")
Part.export([top_cover_obj], stl_housing_path)

stl_base_path = os.path.join(export_dir, "Finger_Keyboard_BottomBase_Bending.stl")
Part.export([bottom_base_obj], stl_base_path)

print("SUCCESS: 2-Piece Zero-Weld Bending Enclosure Generated & Exported!")
print(" - FCStd Project:", fcstd_path)
print(" - STEP (TopCover):", step_housing_path)
print(" - STEP (BottomBase):", step_base_path)
print(" - STEP (Assembly):", step_assembly_path)
print(" - STL (TopCover):", stl_housing_path)
print(" - STL (BottomBase):", stl_base_path)
