import sys
import os
import math

try:
    import FreeCAD
    import Part
    import Mesh
    import MeshPart
except ImportError:
    freecad_path = r"C:\Program Files\FreeCAD 1.1\bin"
    if freecad_path not in sys.path:
        sys.path.append(freecad_path)
    import FreeCAD
    import Part
    import Mesh
    import MeshPart

print(f"=== ARAT 3D Desk Kit Generator (FreeCAD {FreeCAD.Version()}) ===")

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(KIT_DIR, "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

TOL = 0.25  # 3D print sliding fit clearance (mm) on each side

def export_model(shape, filename_base):
    step_file = os.path.join(EXPORTS_DIR, f"{filename_base}.step")
    stl_file = os.path.join(EXPORTS_DIR, f"{filename_base}.stl")
    
    # 1. Export STEP (Industry standard boundary representation)
    shape.exportStep(step_file)
    
    # 2. Export STL (High-precision tessellation for slicers)
    mesh = MeshPart.meshFromShape(shape, LinearDeflection=0.08, AngularDeflection=0.25)
    mesh.write(stl_file)
    
    step_kb = os.path.getsize(step_file) / 1024
    stl_kb = os.path.getsize(stl_file) / 1024
    print(f"  [DONE] {filename_base}:")
    print(f"         STEP: {step_kb:6.1f} KB")
    print(f"         STL:  {stl_kb:6.1f} KB")
    return shape

# ==============================================================================
# 1. SHELF TOP PLATE (선반 상판)
# Dimensions: 220 mm (W) x 130 mm (D) x 10 mm (T)
# Target Surface Height: Z = 370.0 mm
# Fits on 220x220 or 256x256 3D printer beds
# ==============================================================================
print("\n[1/8] Modeling 01_shelf_top_plate...")
plate_w = 220.0
plate_d = 130.0
plate_t = 10.0

plate = Part.makeBox(plate_w, plate_d, plate_t, FreeCAD.Vector(-plate_w/2, -plate_d/2, 0))

# Recessed pocket for Upper Tin (Task T2): ⌀62 mm, depth 3 mm at X = -50, Y = 0
tin_pocket = Part.makeCylinder(31.0, 3.1, FreeCAD.Vector(-50.0, 0, plate_t - 3.0))
plate = plate.cut(tin_pocket)

# Visual placement guide for 50 mm block (Task T1) at X = +50, Y = 0
for dx in [-25.0, 25.0]:
    for dy in [-25.0, 25.0]:
        guide_dot = Part.makeCylinder(1.5, 0.8, FreeCAD.Vector(50.0 + dx, dy, plate_t - 0.7))
        plate = plate.cut(guide_dot)

# Under-plate socket bosses for left and right columns (Column center at X = ±70, Y = 0)
# Boss drops 12 mm down from bottom face (Z = -12 to 0)
for sx in [-70.0, 70.0]:
    boss = Part.makeBox(36.0, 36.0, 12.0, FreeCAD.Vector(sx - 18.0, -18.0, -12.0))
    plate = plate.fuse(boss)

for sx in [-70.0, 70.0]:
    # Socket cavity for Upper Column tenon (20.0 x 20.0 tenon -> 20.5 x 20.5 cavity)
    cav_w = 20.0 + 2*TOL
    cavity = Part.makeBox(cav_w, cav_w, 16.0, FreeCAD.Vector(sx - cav_w/2, -cav_w/2, -12.1))
    plate = plate.cut(cavity)
    
    # Locking pin hole ⌀4.2 mm horizontal through boss at Z = -6.0
    pin_hole = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(sx - 20.0, 0, -6.0), FreeCAD.Vector(1, 0, 0))
    plate = plate.cut(pin_hole)

export_model(plate, "01_shelf_top_plate")


# ==============================================================================
# 2. LOWER COLUMN (하부 기둥 - 좌/우 공용, 2개 출력 필요)
# Effective Height: 180.0 mm (from Z = 5.0 to 185.0)
# Bottom slides 25 mm into Base Foot socket (Z = 5.0 to 30.0)
# Top has 20x20 mm male tenon rising 30 mm (Z = 180.0 to 210.0)
# ==============================================================================
print("\n[2/8] Modeling 02_column_lower...")
col_l_body = Part.makeBox(30.0, 30.0, 180.0, FreeCAD.Vector(-15.0, -15.0, 0))

# Male Tenon at top: 20.0 x 20.0 mm, height 30.0 mm
tenon_top = Part.makeBox(20.0, 20.0, 30.0, FreeCAD.Vector(-10.0, -10.0, 180.0))
col_l = col_l_body.fuse(tenon_top)

# Bottom locking pin hole ⌀4.0 mm at Z = 12.5 mm (mating with Base Foot collar at Z = 17.5 mm)
pin_bot = Part.makeCylinder(2.0, 40.0, FreeCAD.Vector(-20.0, 0, 12.5), FreeCAD.Vector(1, 0, 0))
col_l = col_l.cut(pin_bot)

# Top tenon locking pin hole ⌀4.0 mm at Z = 195.0 mm (15 mm above shoulder)
pin_top = Part.makeCylinder(2.0, 30.0, FreeCAD.Vector(-15.0, 0, 195.0), FreeCAD.Vector(1, 0, 0))
col_l = col_l.cut(pin_top)

# Cross brace connection mortise at Z = 90.0 mm (inward face on X-axis)
# Mortise 15 mm wide, 25 mm tall, 10 mm deep
brace_mortise = Part.makeBox(10.1, 15.0 + 2*TOL, 25.0 + 2*TOL, FreeCAD.Vector(5.0, -(15.0 + 2*TOL)/2, 90.0 - (25.0 + 2*TOL)/2))
col_l = col_l.cut(brace_mortise)

brace_pin = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(0, -20.0, 90.0), FreeCAD.Vector(0, 1, 0))
col_l = col_l.cut(brace_pin)

export_model(col_l, "02_column_lower")


# ==============================================================================
# 3. UPPER COLUMN (상부 기둥 - 좌/우 공용, 2개 출력 필요)
# Effective Height: 175.0 mm (from Z = 185.0 to 360.0)
# Bottom has female socket for Lower Column tenon (depth 31 mm)
# Top has 20x20 mm male tenon (height 15 mm) for Shelf Top Plate
# ==============================================================================
print("\n[3/8] Modeling 03_column_upper...")
col_u_body = Part.makeBox(30.0, 30.0, 175.0, FreeCAD.Vector(-15.0, -15.0, 0))

# Female cavity at bottom (20.5 x 20.5 mm, depth 31.0 mm)
cav_tenon_w = 20.0 + 2*TOL
cav_bot = Part.makeBox(cav_tenon_w, cav_tenon_w, 31.0, FreeCAD.Vector(-cav_tenon_w/2, -cav_tenon_w/2, -0.1))
col_u = col_u_body.cut(cav_bot)

# Top male tenon (20.0 x 20.0 mm, height 15.0 mm)
tenon_top_u = Part.makeBox(20.0, 20.0, 15.0, FreeCAD.Vector(-10.0, -10.0, 175.0))
col_u = col_u_body.fuse(tenon_top_u)

# Bottom pin hole ⌀4.2 mm at Z = 15.0 mm (mating with Lower Column top tenon pin hole)
pin_bot_u = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(-20.0, 0, 15.0), FreeCAD.Vector(1, 0, 0))
col_u = col_u.cut(pin_bot_u)

# Top tenon pin hole ⌀4.0 mm at Z = 181.0 mm (6.0 mm above shoulder, mating with Top Plate boss)
pin_top_u = Part.makeCylinder(2.0, 30.0, FreeCAD.Vector(-15.0, 0, 181.0), FreeCAD.Vector(1, 0, 0))
col_u = col_u.cut(pin_top_u)

export_model(col_u, "03_column_upper")


# ==============================================================================
# 4. BASE FOOT (하부 베이스 받침대 - 좌/우 2개 출력 필요)
# Length: 200 mm along table depth (Y-axis: -100 to +100)
# Width: 50 mm (X-axis: -25 to +25)
# Base floor: 5.0 mm thick (Z = 0 to 5)
# Socket collar: rises from Z = 5 to Z = 30 (depth = 25 mm)
# ==============================================================================
print("\n[4/8] Modeling 04_base_foot...")
foot_len = 200.0
foot_w = 50.0
foot_h = 30.0

foot = Part.makeBox(foot_w, foot_len, 10.0, FreeCAD.Vector(-foot_w/2, -foot_len/2, 0))

# Center collar for column socket (outer 46 x 46 mm, height 30 mm)
collar = Part.makeBox(46.0, 46.0, 20.0, FreeCAD.Vector(-23.0, -23.0, 10.0))
foot = foot.fuse(collar)

# Socket cavity for Lower Column bottom (30.0 x 30.0 -> 30.5 x 30.5 cavity, depth 25.1 mm from Z=5 to Z=30.1)
col_cav_w = 30.0 + 2*TOL
col_cavity = Part.makeBox(col_cav_w, col_cav_w, 25.1, FreeCAD.Vector(-col_cav_w/2, -col_cav_w/2, 5.0))
foot = foot.cut(col_cavity)

# Locking pin hole ⌀4.2 mm horizontal through collar at Z = 17.5 mm (12.5 mm above column seat)
pin_collar = Part.makeCylinder(2.1, 55.0, FreeCAD.Vector(-27.5, 0, 17.5), FreeCAD.Vector(1, 0, 0))
foot = foot.cut(pin_collar)

# Sloped profile on front and rear arms (tapers from 10mm down to 5mm at the tips)
# Front slope cutter: cuts top off between Y=25 and Y=105
poly_f = Part.makePolygon([
    FreeCAD.Vector(-foot_w/2 - 1, 25.0, 10.0),
    FreeCAD.Vector(-foot_w/2 - 1, 105.0, 5.0),
    FreeCAD.Vector(-foot_w/2 - 1, 105.0, 35.0),
    FreeCAD.Vector(-foot_w/2 - 1, 25.0, 35.0),
    FreeCAD.Vector(-foot_w/2 - 1, 25.0, 10.0)
])
cut_f = Part.Face(poly_f).extrude(FreeCAD.Vector(foot_w + 2, 0, 0))
foot = foot.cut(cut_f)

# Rear slope cutter: cuts top off between Y=-25 and Y=-105
poly_r = Part.makePolygon([
    FreeCAD.Vector(-foot_w/2 - 1, -25.0, 10.0),
    FreeCAD.Vector(-foot_w/2 - 1, -105.0, 5.0),
    FreeCAD.Vector(-foot_w/2 - 1, -105.0, 35.0),
    FreeCAD.Vector(-foot_w/2 - 1, -25.0, 35.0),
    FreeCAD.Vector(-foot_w/2 - 1, -25.0, 10.0)
])
cut_r = Part.Face(poly_r).extrude(FreeCAD.Vector(foot_w + 2, 0, 0))
foot = foot.cut(cut_r)

# 4 Recessed pockets for anti-slip rubber pads on bottom (⌀12 mm, depth 1.5 mm)
for y_pad in [-80.0, -35.0, 35.0, 80.0]:
    pad_pocket = Part.makeCylinder(6.0, 1.5, FreeCAD.Vector(0, y_pad, -0.1))
    foot = foot.cut(pad_pocket)

export_model(foot, "04_base_foot")


# ==============================================================================
# 5. CROSS BRACE (기둥 간 횡방향 보강 브레이스 - 1개 출력)
# Spans 110 mm between the inner faces of Left (X=-70+15=-55) and Right (X=+70-15=+55) columns
# Total span: 110 mm + 2x 10 mm tenons = 130 mm
# Prevents any parallelogram sway
# ==============================================================================
print("\n[5/8] Modeling 05_cross_brace...")
brace_span = 110.0 - 2*TOL
brace_body = Part.makeBox(brace_span, 15.0, 25.0, FreeCAD.Vector(-brace_span/2, -7.5, -12.5))

# Left and right tenons (10 mm length, 15x25 cross-section)
tenon_l = Part.makeBox(10.0, 15.0, 25.0, FreeCAD.Vector(-brace_span/2 - 10.0, -7.5, -12.5))
tenon_r = Part.makeBox(10.0, 15.0, 25.0, FreeCAD.Vector(brace_span/2, -7.5, -12.5))
brace = brace_body.fuse(tenon_l).fuse(tenon_r)

# Pin holes ⌀4.2 mm on tenons
pin_bl = Part.makeCylinder(2.1, 20.0, FreeCAD.Vector(-brace_span/2 - 5.0, -10.0, 0), FreeCAD.Vector(0, 1, 0))
pin_br = Part.makeCylinder(2.1, 20.0, FreeCAD.Vector(brace_span/2 + 5.0, -10.0, 0), FreeCAD.Vector(0, 1, 0))
brace = brace.cut(pin_bl).cut(pin_br)

# Weight reduction cutout in center
brace_cut = Part.makeBox(60.0, 16.0, 13.0, FreeCAD.Vector(-30.0, -8.0, -6.5))
brace = brace.cut(brace_cut)

export_model(brace, "05_cross_brace")


# ==============================================================================
# 6. ARAT PINCH TIN CUP / LID (하부 뚜껑 & 상부 뚜껑 - 2개 출력 필요)
# Clinical Standard: Yozbatiran 2008 & Lyle 1981
# Holds ⌀16 mm marble (Task T2)
# Outer: ⌀60 mm, Height: 14 mm, Inner Cavity: ⌀54 mm, Depth: 10 mm
# Concave spherical floor (R=100mm) naturally centers the marble!
# ==============================================================================
print("\n[6/8] Modeling 06_arat_tin_cup...")
tin_od = 60.0
tin_id = 54.0
tin_h = 14.0
tin_floor = 4.0

tin = Part.makeCylinder(tin_od/2, tin_h, FreeCAD.Vector(0, 0, 0))

# Inner cylindrical cavity (depth = 10 mm)
cavity_cyl = Part.makeCylinder(tin_id/2, 10.1, FreeCAD.Vector(0, 0, tin_floor))
tin = tin.cut(cavity_cyl)

# Spherical dish profile in the cavity floor for natural ball centering
# Sphere radius = 100 mm, top of sphere touches Z = tin_floor at outer rim, center drops 1.8 mm
sph_center_z = tin_floor + 100.0 - 1.8
sphere_dish = Part.makeSphere(100.0, FreeCAD.Vector(0, 0, sph_center_z))
tin = tin.cut(sphere_dish)

# Anti-slip rubber pocket on bottom exterior (⌀25 mm, depth 1.0 mm)
bot_pocket = Part.makeCylinder(12.5, 1.1, FreeCAD.Vector(0, 0, -0.1))
tin = tin.cut(bot_pocket)

export_model(tin, "06_arat_tin_cup")


# ==============================================================================
# 7. DESK ALIGNMENT JIG (책상 셋업용 정렬 지그 - 1개 출력)
# Length: 220 mm
# Sets exact clinical placement in 2 seconds without a tape measure:
# - Hook lip on table front edge (0 cm)
# - Notch at 50 mm (5 cm) for Lower Tin proximal edge
# - Step at 200 mm (20 cm) for Shelf Base Foot front edge
# ==============================================================================
print("\n[7/8] Modeling 07_desk_alignment_jig...")
jig_len = 225.0
jig_w = 30.0
jig_t = 6.0

jig = Part.makeBox(jig_w, jig_len, jig_t, FreeCAD.Vector(-jig_w/2, 0, 0))

# Front table lip hanging down 15 mm at Y = 0 (Z = -15 to 0)
lip = Part.makeBox(jig_w, 10.0, 15.0, FreeCAD.Vector(-jig_w/2, 0, -15.0))
jig = jig.fuse(lip)

# Lower Tin locator cradle at Y = 50.0 mm:
# Circular pocket radius 30.0 mm (⌀60 mm tin fits directly)
tin_cradle = Part.makeCylinder(30.2, 4.0, FreeCAD.Vector(0, 50.0 + 30.0, jig_t - 3.5))
jig = jig.cut(tin_cradle)

# Shelf Base Foot alignment stop notch at Y = 200.0 mm:
# Step notch 4.0 mm deep
shelf_stop = Part.makeBox(jig_w + 2, 25.0, 4.0, FreeCAD.Vector(-jig_w/2 - 1, 200.0, jig_t - 3.5))
jig = jig.cut(shelf_stop)

export_model(jig, "07_desk_alignment_jig")


# ==============================================================================
# 8. QUICK LOCKING PIN (조립 고정용 핀 - 8개 출력 권장)
# ⌀4.0 mm dowel with ergonomic pull-ring head
# Replaces M4 screws for 100% tool-less snap assembly
# ==============================================================================
print("\n[8/8] Modeling 08_locking_pin...")
pin_shaft = Part.makeCylinder(1.95, 38.0, FreeCAD.Vector(0, 0, 0))

# Head base
head_base = Part.makeCylinder(4.0, 5.0, FreeCAD.Vector(0, 0, -5.0))
ring_torus = Part.makeTorus(6.0, 2.0, FreeCAD.Vector(0, 0, -10.0), FreeCAD.Vector(0, 1, 0))
pin_full = pin_shaft.fuse(head_base).fuse(ring_torus)

export_model(pin_full, "08_locking_pin")


# ==============================================================================
# 9. COMPLETE ASSEMBLED MODEL (00_arat_complete_assembly)
# Full 3D assembly verification at exact clinical height:
# Table surface: Z = 0.0
# Base floor: Z = 0 to 5.0
# Lower column: Z = 5.0 to 185.0
# Upper column: Z = 185.0 to 360.0
# Top shelf plate: Z = 360.0 to 370.0
# Top Shelf Surface: Z = 370.0 mm (37.0 cm) EXACT!
# ==============================================================================
print("\n[VERIFICATION] Creating full assembled model...")

# Left and Right Base Feet (at X = -70 and +70, resting at Z = 0)
foot_left = foot.copy()
foot_left.translate(FreeCAD.Vector(-70.0, 0, 0))
foot_right = foot.copy()
foot_right.translate(FreeCAD.Vector(70.0, 0, 0))

# Left and Right Lower Columns (resting at Z = 5.0)
col_l_left = col_l.copy()
col_l_left.translate(FreeCAD.Vector(-70.0, 0, 5.0))
col_l_right = col_l.copy()
col_l_right.translate(FreeCAD.Vector(70.0, 0, 5.0))

# Left and Right Upper Columns (resting at Z = 185.0)
col_u_left = col_u.copy()
col_u_left.translate(FreeCAD.Vector(-70.0, 0, 185.0))
col_u_right = col_u.copy()
col_u_right.translate(FreeCAD.Vector(70.0, 0, 185.0))

# Cross brace at Z = 95.0
brace_asm = brace.copy()
brace_asm.translate(FreeCAD.Vector(0, 0, 95.0))

# Top Shelf Plate (resting on upper column shoulders at Z = 360.0)
# Top face is at Z = 360.0 + 10.0 = 370.0 mm!
plate_asm = plate.copy()
plate_asm.translate(FreeCAD.Vector(0, 0, 360.0))

# Upper Tin placed in the pocket of the shelf (pocket floor at Z = 367.0)
tin_upper = tin.copy()
tin_upper.translate(FreeCAD.Vector(-50.0, 0, 367.0))

# Lower Tin placed on the desk at (X = -50, Y = -200 + 50 = -150 mm, Z = 0)
tin_lower = tin.copy()
tin_lower.translate(FreeCAD.Vector(-50.0, -150.0, 0))

full_assembly = foot_left.fuse(foot_right).fuse(col_l_left).fuse(col_l_right).fuse(col_u_left).fuse(col_u_right).fuse(brace_asm).fuse(plate_asm).fuse(tin_upper).fuse(tin_lower)

export_model(full_assembly, "00_arat_complete_assembly")

bbox = full_assembly.BoundBox
print("\n========================================================")
print(f"ASSEMBLY BOUNDING BOX VERIFICATION:")
print(f"  X Range: {bbox.XMin:6.1f} to {bbox.XMax:6.1f} mm  (Width  = {bbox.XLength:6.1f} mm)")
print(f"  Y Range: {bbox.YMin:6.1f} to {bbox.YMax:6.1f} mm  (Depth  = {bbox.YLength:6.1f} mm)")
print(f"  Z Range: {bbox.ZMin:6.1f} to {bbox.ZMax:6.1f} mm  (Height = {bbox.ZLength:6.1f} mm)")
print(f"  -> Table Surface:           Z = 0.0 mm")
print(f"  -> Top Shelf Surface (T1):  Z = {plate_asm.BoundBox.ZMax:6.1f} mm (37.0 cm EXACT!)")
print("========================================================\n")
