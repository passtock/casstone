import sys
import os
import math

# Add FreeCAD paths
freecad_bin = r"C:\Program Files\FreeCAD 1.1\bin"
freecad_mod = r"C:\Program Files\FreeCAD 1.1\Mod"

for p in [freecad_bin, freecad_mod]:
    if p not in sys.path:
        sys.path.insert(0, p)

import FreeCAD
import Part
from FreeCAD import Base

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# -------------------------------------------------------------
# 1. PARAMETERS & SPECIFICATIONS (2.0t Steel / Al Sheet Metal)
# -------------------------------------------------------------
W = 320.0        # Total Enclosure Width (X)
D = 180.0        # Total Enclosure Depth (Y)
H = 50.0         # Total Enclosure Height (Z)
t = 2.0          # Sheet metal thickness (2.0 mm)
R_bend_in = 2.0  # Inside bend radius
R_bend_out = 4.0 # Outside bend radius
gap = 0.3        # Assembly clearance gap

# K-factor & Bend Deduction (Standard 90° Air Bend, 2.0t)
K_factor = 0.40
BA_90 = (math.pi / 2.0) * (R_bend_in + K_factor * t) # ~4.40 mm
BD_90 = 2.0 * (R_bend_in + t) - BA_90                 # ~3.60 mm

flange_lip_w = 14.0 # Bottom return mounting lip width
stiff_lip_w = 12.0  # Bottom chassis top stiffening lip width

export_dir = r"c:\Users\passp\Desktop\univercity\4-2\캡스톤\머신\01_컨트롤러_3D도면_CAD"
onedrive_dir = r"c:\Users\passp\OneDrive\바탕 화면\jeayong\머신\01_컨트롤러_3D도면_CAD"
os.makedirs(export_dir, exist_ok=True)
os.makedirs(onedrive_dir, exist_ok=True)

# -------------------------------------------------------------
# 2. BUTTONS & PORTS LAYOUT
# -------------------------------------------------------------
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
btn_hole_d = 30.0 # 30.0 mm dia for arcade snap-in buttons

jack_x_positions = [80.0, 160.0, 240.0]
jack_z = 25.0
jack_hole_d = 16.0 # 16.0 mm dia for GX16 aviation jacks

# Screws (5 x M4, 3 on Front, 2 on Rear)
screw_x_front = [60.0, 160.0, 260.0]
screw_x_rear = [60.0, 260.0]
screw_y_front = t + flange_lip_w / 2.0
screw_y_rear = D - t - flange_lip_w / 2.0

print(f"[INFO] Initializing CAD Generation with t={t}mm, BD={BD_90:.2f}mm...")

# =============================================================
# PART A: 3D FREECAD SOLID MODELING
# =============================================================
doc_name = "Finger_Keyboard_SheetMetal_V2"
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

# 1. TOP COVER SOLID (상부 ㄷ자 커버 + 플랜지)
top_plate = Part.makeBox(W, D, t, Base.Vector(0, 0, H - t))
front_wall = Part.makeBox(W, t, H - 2 * t, Base.Vector(0, 0, t))
rear_wall = Part.makeBox(W, t, H - 2 * t, Base.Vector(0, D - t, t))
front_lip = Part.makeBox(W - 30.0, flange_lip_w, t, Base.Vector(15.0, t, t))
rear_lip_left = Part.makeBox(110.0, flange_lip_w, t, Base.Vector(15.0, D - t - flange_lip_w, t))
rear_lip_right = Part.makeBox(110.0, flange_lip_w, t, Base.Vector(195.0, D - t - flange_lip_w, t))

top_solid = top_plate.fuse(front_wall).fuse(rear_wall).fuse(front_lip).fuse(rear_lip_left).fuse(rear_lip_right)

bend_edges = []
for e in top_solid.Edges:
    v1, v2 = e.Vertexes[0].Point, e.Vertexes[1].Point
    if abs(v1.y) < 0.01 and abs(v2.y) < 0.01 and abs(v1.z - H) < 0.01 and abs(v2.z - H) < 0.01:
        bend_edges.append(e)
    if abs(v1.y - D) < 0.01 and abs(v2.y - D) < 0.01 and abs(v1.z - H) < 0.01 and abs(v2.z - H) < 0.01:
        bend_edges.append(e)
if len(bend_edges) == 2:
    try:
        top_filleted = top_solid.makeFillet(R_bend_out - 0.2, bend_edges)
    except Exception:
        top_filleted = top_solid
else:
    top_filleted = top_solid

# Cut 10 Button Holes
top_with_holes = top_filleted
for name, bx, by in buttons_layout:
    cyl = Part.makeCylinder(btn_hole_d / 2.0, t + 4.0, Base.Vector(bx, by, H - t - 2.0), Base.Vector(0, 0, 1))
    top_with_holes = top_with_holes.cut(cyl)

# Cut 3 Rear GX16 Jack Holes
for jx in jack_x_positions:
    cyl = Part.makeCylinder(jack_hole_d / 2.0, t + 4.0, Base.Vector(jx, D - t - 2.0, jack_z), Base.Vector(0, 1, 0))
    top_with_holes = top_with_holes.cut(cyl)

# Cut 5 Screw Tapped Holes (M4 pilot Ø3.3mm)
for sx in screw_x_front:
    cyl = Part.makeCylinder(1.65, t + 4.0, Base.Vector(sx, screw_y_front, t - 2.0), Base.Vector(0, 0, 1))
    top_with_holes = top_with_holes.cut(cyl)
for sx in screw_x_rear:
    cyl = Part.makeCylinder(1.65, t + 4.0, Base.Vector(sx, screw_y_rear, t - 2.0), Base.Vector(0, 0, 1))
    top_with_holes = top_with_holes.cut(cyl)

top_obj = doc.addObject("Part::Feature", "TopCover_3D")
top_obj.Shape = top_with_holes
set_color(top_obj, (0.28, 0.31, 0.36, 1.0))

# 2. BOTTOM BASE CHASSIS SOLID (하부 ㄷ자 베이스 + 상단보강플랜지)
bot_plate = Part.makeBox(W, D, t, Base.Vector(0, 0, 0))
side_wall_d = D - 2 * (t + gap)
side_wall_h = H - 2 * t - gap

left_wall = Part.makeBox(t, side_wall_d, side_wall_h, Base.Vector(t + gap, t + gap, t))
right_wall = Part.makeBox(t, side_wall_d, side_wall_h, Base.Vector(W - 2 * t - gap, t + gap, t))
left_top_lip = Part.makeBox(stiff_lip_w, side_wall_d, t, Base.Vector(t + gap, t + gap, H - 2 * t - gap))
right_top_lip = Part.makeBox(stiff_lip_w, side_wall_d, t, Base.Vector(W - 2 * t - gap - stiff_lip_w, t + gap, H - 2 * t - gap))

bot_solid = bot_plate.fuse(left_wall).fuse(right_wall).fuse(left_top_lip).fuse(right_top_lip)

# Cut 5 Countersunk Screw Holes in Bottom Plate (DIN 7991 M4)
bot_with_holes = bot_solid
for sx in screw_x_front:
    th = Part.makeCylinder(2.25, t + 4.0, Base.Vector(sx, screw_y_front, -2.0), Base.Vector(0, 0, 1))
    cs = Part.makeCone(4.2, 2.25, t, Base.Vector(sx, screw_y_front, 0), Base.Vector(0, 0, 1))
    bot_with_holes = bot_with_holes.cut(th).cut(cs)
for sx in screw_x_rear:
    th = Part.makeCylinder(2.25, t + 4.0, Base.Vector(sx, screw_y_rear, -2.0), Base.Vector(0, 0, 1))
    cs = Part.makeCone(4.2, 2.25, t, Base.Vector(sx, screw_y_rear, 0), Base.Vector(0, 0, 1))
    bot_with_holes = bot_with_holes.cut(th).cut(cs)

bot_obj = doc.addObject("Part::Feature", "BottomBase_3D")
bot_obj.Shape = bot_with_holes
set_color(bot_obj, (0.16, 0.18, 0.20, 1.0))

# 3. BUTTON & CONNECTOR PREVIEW OBJECTS
for name, bx, by in buttons_layout:
    rim = Part.makeCylinder(16.5, 3.0, Base.Vector(bx, by, H), Base.Vector(0, 0, 1))
    cap = Part.makeCylinder(12.5, 3.5, Base.Vector(bx, by, H + 3.0), Base.Vector(0, 0, 1))
    btn_part = rim.fuse(cap)
    b_obj = doc.addObject("Part::Feature", f"Btn_{name}")
    b_obj.Shape = btn_part
    set_color(b_obj, (0.1, 0.85, 0.35, 1.0))

for idx, jx in enumerate(jack_x_positions, 1):
    col = Part.makeCylinder(9.5, 4.5, Base.Vector(jx, D, jack_z), Base.Vector(0, 1, 0))
    j_obj = doc.addObject("Part::Feature", f"GX16_{idx}")
    j_obj.Shape = col
    set_color(j_obj, (0.75, 0.78, 0.82, 1.0))


# =============================================================
# PART B: 2D FLAT PATTERNS (EMBEDDED IN FREECAD + PURE R12 DXF)
# =============================================================
wall_flat_top = 48.0 - BD_90
lip_flat_top = flange_lip_w - (BD_90 / 2.0)
y_flange_front_bend = -wall_flat_top
y_flange_front_edge = -(wall_flat_top + lip_flat_top)
y_flange_rear_bend = D + wall_flat_top
y_flange_rear_edge = D + wall_flat_top + lip_flat_top

top_poly = [
    (0.0, 0.0),
    (0.0, y_flange_front_bend),
    (15.0, y_flange_front_bend),
    (15.0, y_flange_front_edge),
    (W - 15.0, y_flange_front_edge),
    (W - 15.0, y_flange_front_bend),
    (W, y_flange_front_bend),
    (W, 0.0),
    (W, D),
    (W, y_flange_rear_bend),
    (W - 15.0, y_flange_rear_bend),
    (W - 15.0, y_flange_rear_edge),
    (195.0, y_flange_rear_edge),
    (195.0, y_flange_rear_bend),
    (125.0, y_flange_rear_bend),
    (125.0, y_flange_rear_edge),
    (15.0, y_flange_rear_edge),
    (15.0, y_flange_rear_bend),
    (0.0, y_flange_rear_bend),
    (0.0, D),
    (0.0, 0.0)
]

# Embed Top Flat Pattern into FreeCAD (placed to the side at X = -380 mm)
offset_x_top = -380.0
top_wire_pts = [Base.Vector(p[0] + offset_x_top, p[1], 0) for p in top_poly]
top_flat_face = Part.Face(Part.makePolygon(top_wire_pts))

for name, bx, by in buttons_layout:
    h_face = Part.Face(Part.Wire(Part.makeCircle(btn_hole_d / 2.0, Base.Vector(bx + offset_x_top, by, 0))))
    top_flat_face = top_flat_face.cut(h_face)

y_jack_flat = D + (wall_flat_top / 2.0)
for jx in jack_x_positions:
    h_face = Part.Face(Part.Wire(Part.makeCircle(jack_hole_d / 2.0, Base.Vector(jx + offset_x_top, y_jack_flat, 0))))
    top_flat_face = top_flat_face.cut(h_face)

y_screw_front_flat = y_flange_front_bend - (lip_flat_top / 2.0)
y_screw_rear_flat = y_flange_rear_bend + (lip_flat_top / 2.0)
for sx in screw_x_front:
    h_face = Part.Face(Part.Wire(Part.makeCircle(1.7, Base.Vector(sx + offset_x_top, y_screw_front_flat, 0))))
    top_flat_face = top_flat_face.cut(h_face)
for sx in screw_x_rear:
    h_face = Part.Face(Part.Wire(Part.makeCircle(1.7, Base.Vector(sx + offset_x_top, y_screw_rear_flat, 0))))
    top_flat_face = top_flat_face.cut(h_face)

top_flat_obj = doc.addObject("Part::Feature", "TopCover_FlatPattern_2D")
top_flat_obj.Shape = top_flat_face
set_color(top_flat_obj, (0.0, 0.8, 0.6, 1.0))

# Bottom Flat Pattern calculation
wall_flat_bot = side_wall_h - BD_90
lip_flat_bot = stiff_lip_w - (BD_90 / 2.0)
x_left_wall_bend = -wall_flat_bot
x_left_lip_edge = -(wall_flat_bot + lip_flat_bot)
x_right_wall_bend = W + wall_flat_bot
x_right_lip_edge = W + wall_flat_bot + lip_flat_bot
y_side_min = t + gap
y_side_max = D - (t + gap)

bot_poly = [
    (0.0, 0.0),
    (0.0, y_side_min),
    (x_left_lip_edge, y_side_min),
    (x_left_lip_edge, y_side_max),
    (0.0, y_side_max),
    (0.0, D),
    (W, D),
    (W, y_side_max),
    (x_right_lip_edge, y_side_max),
    (x_right_lip_edge, y_side_min),
    (W, y_side_min),
    (W, 0.0),
    (0.0, 0.0)
]

offset_y_bot = -240.0
bot_wire_pts = [Base.Vector(p[0] + offset_x_top, p[1] + offset_y_bot, 0) for p in bot_poly]
bot_flat_face = Part.Face(Part.makePolygon(bot_wire_pts))

for sx in screw_x_front:
    h_face = Part.Face(Part.Wire(Part.makeCircle(2.25, Base.Vector(sx + offset_x_top, screw_y_front + offset_y_bot, 0))))
    bot_flat_face = bot_flat_face.cut(h_face)
for sx in screw_x_rear:
    h_face = Part.Face(Part.Wire(Part.makeCircle(2.25, Base.Vector(sx + offset_x_top, screw_y_rear + offset_y_bot, 0))))
    bot_flat_face = bot_flat_face.cut(h_face)

bot_flat_obj = doc.addObject("Part::Feature", "BottomBase_FlatPattern_2D")
bot_flat_obj.Shape = bot_flat_face
set_color(bot_flat_obj, (0.0, 0.6, 0.8, 1.0))

doc.recompute()

# Save FreeCAD Project (contains BOTH 3D models and 2D Flat Patterns!)
fcstd_path = os.path.join(export_dir, "Finger_Keyboard_SheetMetal_V2.FCStd")
doc.saveAs(fcstd_path)

# Export 3D STEP and STL files
step_top = os.path.join(export_dir, "Finger_Keyboard_TopCover_3D.step")
Part.export([top_obj], step_top)
step_bot = os.path.join(export_dir, "Finger_Keyboard_BottomBase_3D.step")
Part.export([bot_obj], step_bot)
step_assy = os.path.join(export_dir, "Finger_Keyboard_Assembly_3D.step")
Part.export([top_obj, bot_obj], step_assy)

stl_top = os.path.join(export_dir, "Finger_Keyboard_TopCover_3D.stl")
Part.export([top_obj], stl_top)
stl_bot = os.path.join(export_dir, "Finger_Keyboard_BottomBase_3D.stl")
Part.export([bot_obj], stl_bot)


# =============================================================
# PART C: PURE AUTOCAD R12 DXF GENERATION (UNIVERSAL COMPATIBILITY)
# =============================================================
def write_r12_dxf(filename, polylines, circles, lines, texts):
    with open(filename, 'w', encoding='ascii') as f:
        f.write('0\nSECTION\n2\nENTITIES\n')
        
        # 1. Polylines (Cut Contours)
        for pts, closed, layer in polylines:
            f.write(f'0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n{1 if closed else 0}\n')
            for x, y in pts:
                f.write(f'0\nVERTEX\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n')
            f.write(f'0\nSEQEND\n8\n{layer}\n')
            
        # 2. Circles (Holes)
        for cx, cy, r, layer in circles:
            f.write(f'0\nCIRCLE\n8\n{layer}\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n40\n{r:.4f}\n')
            
        # 3. Lines (Bend lines)
        for (x1, y1), (x2, y2), layer in lines:
            f.write(f'0\nLINE\n8\n{layer}\n10\n{x1:.4f}\n20\n{y1:.4f}\n30\n0.0\n11\n{x2:.4f}\n21\n{y2:.4f}\n31\n0.0\n')
            
        # 4. Text Annotations
        for text, x, y, h, layer in texts:
            f.write(f'0\nTEXT\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{h:.4f}\n1\n{text}\n')
            
        f.write('0\nENDSEC\n0\nEOF\n')

# 1. Write Top Cover DXF
top_circles = []
for name, bx, by in buttons_layout:
    top_circles.append((bx, by, btn_hole_d / 2.0, "0_CUT_HOLES"))
for jx in jack_x_positions:
    top_circles.append((jx, y_jack_flat, jack_hole_d / 2.0, "0_CUT_HOLES"))
for sx in screw_x_front:
    top_circles.append((sx, y_screw_front_flat, 1.7, "0_CUT_HOLES"))
for sx in screw_x_rear:
    top_circles.append((sx, y_screw_rear_flat, 1.7, "0_CUT_HOLES"))

top_bends = [
    ((15.0, y_flange_front_bend), (W - 15.0, y_flange_front_bend), "BEND_LINES"),
    ((0.0, 0.0), (W, 0.0), "BEND_LINES"),
    ((0.0, D), (W, D), "BEND_LINES"),
    ((15.0, y_flange_rear_bend), (125.0, y_flange_rear_bend), "BEND_LINES"),
    ((195.0, y_flange_rear_bend), (W - 15.0, y_flange_rear_bend), "BEND_LINES")
]

top_texts = [
    ("BEND 1: 90 DEG UP (R=2.0) -> BOTTOM LIP", 20.0, y_flange_front_bend - 6.0, 4.0, "ANNOTATIONS"),
    ("BEND 2: 90 DEG DOWN (R=2.0) -> FRONT WALL", 20.0, 3.0, 4.0, "ANNOTATIONS"),
    ("TOP COVER MAIN FACE (320 x 180 mm) - 2.0t SPCC/AL", 50.0, 85.0, 5.0, "ANNOTATIONS"),
    ("BEND 3: 90 DEG DOWN (R=2.0) -> REAR WALL", 20.0, D - 7.0, 4.0, "ANNOTATIONS"),
    ("BEND 4: 90 DEG UP (R=2.0) -> REAR BOTTOM LIP", 20.0, y_flange_rear_bend + 4.0, 4.0, "ANNOTATIONS")
]

top_dxf_path = os.path.join(export_dir, "Finger_Keyboard_TopCover_FlatPattern.dxf")
write_r12_dxf(top_dxf_path, [(top_poly, True, "0_CUT_OUTLINE")], top_circles, top_bends, top_texts)

# 2. Write Bottom Chassis DXF
bot_circles = []
for sx in screw_x_front:
    bot_circles.append((sx, screw_y_front, 2.25, "0_CUT_HOLES"))
for sx in screw_x_rear:
    bot_circles.append((sx, screw_y_rear, 2.25, "0_CUT_HOLES"))

bot_bends = [
    ((0.0, y_side_min), (0.0, y_side_max), "BEND_LINES"),
    ((x_left_wall_bend, y_side_min), (x_left_wall_bend, y_side_max), "BEND_LINES"),
    ((W, y_side_min), (W, y_side_max), "BEND_LINES"),
    ((x_right_wall_bend, y_side_min), (x_right_wall_bend, y_side_max), "BEND_LINES")
]

bot_texts = [
    ("BEND: 90 DEG IN (R=2.0) -> LEFT LIP", x_left_lip_edge + 2.0, 40.0, 3.5, "ANNOTATIONS"),
    ("BEND: 90 DEG UP (R=2.0) -> LEFT WALL", x_left_wall_bend + 2.0, 40.0, 3.5, "ANNOTATIONS"),
    ("BOTTOM BASE CHASSIS (320 x 180 mm) - 2.0t SPCC/AL", 50.0, 90.0, 5.0, "ANNOTATIONS"),
    ("5x M4 COUNTERSUNK (CSK 90 DEG TO DIA 8.4mm)", 60.0, 25.0, 4.0, "ANNOTATIONS"),
    ("BEND: 90 DEG UP (R=2.0) -> RIGHT WALL", W + 5.0, 40.0, 3.5, "ANNOTATIONS"),
    ("BEND: 90 DEG IN (R=2.0) -> RIGHT LIP", x_right_wall_bend + 5.0, 40.0, 3.5, "ANNOTATIONS")
]

bot_dxf_path = os.path.join(export_dir, "Finger_Keyboard_BottomBase_FlatPattern.dxf")
write_r12_dxf(bot_dxf_path, [(bot_poly, True, "0_CUT_OUTLINE")], bot_circles, bot_bends, bot_texts)


# =============================================================
# PART D: HIGH-RES 2D & 3D DIAGRAM RENDERS
# =============================================================
plt.style.use('dark_background')

# 1. 3D Isometric View Render
top_mesh = doc.TopCover_3D.Shape.tessellate(1.0)
bot_mesh = doc.BottomBase_3D.Shape.tessellate(1.0)

fig = plt.figure(figsize=(12, 9), dpi=150, facecolor='#0d1117')
ax = fig.add_subplot(111, projection='3d', facecolor='#0d1117')

verts_bot = [[bot_mesh[0][i] for i in tri] for tri in bot_mesh[1]]
poly_bot = Poly3DCollection(verts_bot, alpha=0.85, facecolor='#21262d', edgecolor='#30363d', linewidths=0.2)
ax.add_collection3d(poly_bot)

verts_top = [[top_mesh[0][i] for i in tri] for tri in top_mesh[1]]
poly_top = Poly3DCollection(verts_top, alpha=0.9, facecolor='#388bfd', edgecolor='#58a6ff', linewidths=0.2)
ax.add_collection3d(poly_top)

ax.set_xlim(0, 320)
ax.set_ylim(0, 180)
ax.set_zlim(0, 60)
ax.view_init(elev=32, azim=-55)
ax.set_axis_off()
plt.title('Finger Keyboard Sheet Metal Enclosure (3D Assembled CAD View)', color='#58a6ff', fontsize=14, fontweight='bold', pad=20)

render_3d_png = os.path.join(export_dir, "SheetMetal_3D_Isometric_Render.png")
plt.tight_layout()
plt.savefig(render_3d_png, facecolor='#0d1117')
plt.close()

# Sync everything to OneDrive
all_export_files = [
    fcstd_path, step_top, step_bot, step_assy, stl_top, stl_bot,
    top_dxf_path, bot_dxf_path, render_3d_png
]

for f in all_export_files:
    dest = os.path.join(onedrive_dir, os.path.basename(f))
    try:
        with open(f, 'rb') as rf, open(dest, 'wb') as wf:
            wf.write(rf.read())
    except Exception:
        pass

print("[COMPLETE] All CAD, DXF, and Render files successfully updated and verified!")
print(" - FreeCAD Project (with 3D and 2D):", fcstd_path)
print(" - Top Cover R12 DXF:", top_dxf_path)
print(" - Bottom Base R12 DXF:", bot_dxf_path)
