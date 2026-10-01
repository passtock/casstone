import sys
import os
import math

try:
    import FreeCAD
    import Part
    import MeshPart
except ImportError:
    freecad_path = r"C:\Program Files\FreeCAD 1.1\bin"
    if freecad_path not in sys.path:
        sys.path.append(freecad_path)
    import FreeCAD
    import Part
    import MeshPart

KIT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(KIT_DIR, "exports")
PLATES_DIR = os.path.join(KIT_DIR, "print_plates")
os.makedirs(PLATES_DIR, exist_ok=True)

TOL = 0.25

def export_plate(shape, filename_base, desc=""):
    step_file = os.path.join(PLATES_DIR, f"{filename_base}.step")
    stl_file = os.path.join(PLATES_DIR, f"{filename_base}.stl")
    
    shape.exportStep(step_file)
    mesh = MeshPart.meshFromShape(shape, LinearDeflection=0.08, AngularDeflection=0.25)
    mesh.write(stl_file)
    
    bbox = shape.BoundBox
    print(f"\n========================================================")
    print(f"[PLATE READY] {filename_base}.stl  ({desc})")
    print(f"  Footprint: X [{bbox.XMin:5.1f} ~ {bbox.XMax:5.1f}] ({bbox.XLength:5.1f} mm)")
    print(f"             Y [{bbox.YMin:5.1f} ~ {bbox.YMax:5.1f}] ({bbox.YLength:5.1f} mm)")
    print(f"             Z [{bbox.ZMin:5.1f} ~ {bbox.ZMax:5.1f}] ({bbox.ZLength:5.1f} mm)")
    print(f"  File size: STL {os.path.getsize(stl_file)/1024:6.1f} KB | STEP {os.path.getsize(step_file)/1024:6.1f} KB")
    print(f"========================================================")

# ==============================================================================
# Helper functions to build base geometry
# ==============================================================================
def make_base_foot():
    foot_len = 200.0
    foot_w = 50.0
    foot_h = 30.0
    foot = Part.makeBox(foot_w, foot_len, 10.0, FreeCAD.Vector(-foot_w/2, -foot_len/2, 0))
    collar = Part.makeBox(46.0, 46.0, 20.0, FreeCAD.Vector(-23.0, -23.0, 10.0))
    foot = foot.fuse(collar)
    col_cav_w = 30.0 + 2*TOL
    col_cavity = Part.makeBox(col_cav_w, col_cav_w, 25.1, FreeCAD.Vector(-col_cav_w/2, -col_cav_w/2, 5.0))
    foot = foot.cut(col_cavity)
    pin_collar = Part.makeCylinder(2.1, 55.0, FreeCAD.Vector(-27.5, 0, 17.5), FreeCAD.Vector(1, 0, 0))
    foot = foot.cut(pin_collar)
    
    poly_f = Part.makePolygon([
        FreeCAD.Vector(-foot_w/2 - 1, 25.0, 10.0),
        FreeCAD.Vector(-foot_w/2 - 1, 105.0, 5.0),
        FreeCAD.Vector(-foot_w/2 - 1, 105.0, 35.0),
        FreeCAD.Vector(-foot_w/2 - 1, 25.0, 35.0),
        FreeCAD.Vector(-foot_w/2 - 1, 25.0, 10.0)
    ])
    cut_f = Part.Face(poly_f).extrude(FreeCAD.Vector(foot_w + 2, 0, 0))
    foot = foot.cut(cut_f)

    poly_r = Part.makePolygon([
        FreeCAD.Vector(-foot_w/2 - 1, -25.0, 10.0),
        FreeCAD.Vector(-foot_w/2 - 1, -105.0, 5.0),
        FreeCAD.Vector(-foot_w/2 - 1, -105.0, 35.0),
        FreeCAD.Vector(-foot_w/2 - 1, -25.0, 35.0),
        FreeCAD.Vector(-foot_w/2 - 1, -25.0, 10.0)
    ])
    cut_r = Part.Face(poly_r).extrude(FreeCAD.Vector(foot_w + 2, 0, 0))
    foot = foot.cut(cut_r)

    for y_pad in [-80.0, -35.0, 35.0, 80.0]:
        pad_pocket = Part.makeCylinder(6.0, 1.5, FreeCAD.Vector(0, y_pad, -0.1))
        foot = foot.cut(pad_pocket)
    return foot

def make_column_lower():
    col_l_body = Part.makeBox(30.0, 30.0, 180.0, FreeCAD.Vector(-15.0, -15.0, 0))
    tenon_top = Part.makeBox(20.0, 20.0, 30.0, FreeCAD.Vector(-10.0, -10.0, 180.0))
    col_l = col_l_body.fuse(tenon_top)
    pin_bot = Part.makeCylinder(2.0, 40.0, FreeCAD.Vector(-20.0, 0, 12.5), FreeCAD.Vector(1, 0, 0))
    col_l = col_l.cut(pin_bot)
    pin_top = Part.makeCylinder(2.0, 30.0, FreeCAD.Vector(-15.0, 0, 195.0), FreeCAD.Vector(1, 0, 0))
    col_l = col_l.cut(pin_top)
    brace_mortise = Part.makeBox(10.1, 15.0 + 2*TOL, 25.0 + 2*TOL, FreeCAD.Vector(5.0, -(15.0 + 2*TOL)/2, 90.0 - (25.0 + 2*TOL)/2))
    col_l = col_l.cut(brace_mortise)
    brace_pin = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(0, -20.0, 90.0), FreeCAD.Vector(0, 1, 0))
    col_l = col_l.cut(brace_pin)
    return col_l

def make_column_upper():
    col_u_body = Part.makeBox(30.0, 30.0, 175.0, FreeCAD.Vector(-15.0, -15.0, 0))
    cav_tenon_w = 20.0 + 2*TOL
    cav_bot = Part.makeBox(cav_tenon_w, cav_tenon_w, 31.0, FreeCAD.Vector(-cav_tenon_w/2, -cav_tenon_w/2, -0.1))
    col_u = col_u_body.cut(cav_bot)
    tenon_top_u = Part.makeBox(20.0, 20.0, 15.0, FreeCAD.Vector(-10.0, -10.0, 175.0))
    col_u = col_u_body.fuse(tenon_top_u)
    pin_bot_u = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(-20.0, 0, 15.0), FreeCAD.Vector(1, 0, 0))
    col_u = col_u.cut(pin_bot_u)
    pin_top_u = Part.makeCylinder(2.0, 30.0, FreeCAD.Vector(-15.0, 0, 181.0), FreeCAD.Vector(1, 0, 0))
    col_u = col_u.cut(pin_top_u)
    return col_u

def make_shelf_top_plate():
    plate_w = 220.0
    plate_d = 130.0
    plate_t = 10.0
    plate = Part.makeBox(plate_w, plate_d, plate_t, FreeCAD.Vector(-plate_w/2, -plate_d/2, 0))
    tin_pocket = Part.makeCylinder(31.0, 3.1, FreeCAD.Vector(-50.0, 0, plate_t - 3.0))
    plate = plate.cut(tin_pocket)
    for dx in [-25.0, 25.0]:
        for dy in [-25.0, 25.0]:
            guide_dot = Part.makeCylinder(1.5, 0.8, FreeCAD.Vector(50.0 + dx, dy, plate_t - 0.7))
            plate = plate.cut(guide_dot)
    for sx in [-70.0, 70.0]:
        boss = Part.makeBox(36.0, 36.0, 12.0, FreeCAD.Vector(sx - 18.0, -18.0, -12.0))
        plate = plate.fuse(boss)
    for sx in [-70.0, 70.0]:
        cav_w = 20.0 + 2*TOL
        cavity = Part.makeBox(cav_w, cav_w, 16.0, FreeCAD.Vector(sx - cav_w/2, -cav_w/2, -12.1))
        plate = plate.cut(cavity)
        pin_hole = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(sx - 20.0, 0, -6.0), FreeCAD.Vector(1, 0, 0))
        plate = plate.cut(pin_hole)
    # Move plate so its lowest point (bosses) is at Z = 0
    plate.translate(FreeCAD.Vector(0, 0, 12.0))
    return plate

def make_cross_brace():
    brace_span = 110.0 - 2*TOL
    brace_body = Part.makeBox(brace_span, 15.0, 25.0, FreeCAD.Vector(-brace_span/2, -7.5, 0))
    tenon_l = Part.makeBox(10.0, 15.0, 25.0, FreeCAD.Vector(-brace_span/2 - 10.0, -7.5, 0))
    tenon_r = Part.makeBox(10.0, 15.0, 25.0, FreeCAD.Vector(brace_span/2, -7.5, 0))
    brace = brace_body.fuse(tenon_l).fuse(tenon_r)
    pin_bl = Part.makeCylinder(2.1, 20.0, FreeCAD.Vector(-brace_span/2 - 5.0, -10.0, 12.5), FreeCAD.Vector(0, 1, 0))
    pin_br = Part.makeCylinder(2.1, 20.0, FreeCAD.Vector(brace_span/2 + 5.0, -10.0, 12.5), FreeCAD.Vector(0, 1, 0))
    brace = brace.cut(pin_bl).cut(pin_br)
    brace_cut = Part.makeBox(60.0, 16.0, 13.0, FreeCAD.Vector(-30.0, -8.0, 6.0))
    brace = brace.cut(brace_cut)
    return brace

def make_tin_cup():
    tin_od = 60.0
    tin_id = 54.0
    tin_h = 14.0
    tin_floor = 4.0
    tin = Part.makeCylinder(tin_od/2, tin_h, FreeCAD.Vector(0, 0, 0))
    cavity_cyl = Part.makeCylinder(tin_id/2, 10.1, FreeCAD.Vector(0, 0, tin_floor))
    tin = tin.cut(cavity_cyl)
    sph_center_z = tin_floor + 100.0 - 1.8
    sphere_dish = Part.makeSphere(100.0, FreeCAD.Vector(0, 0, sph_center_z))
    tin = tin.cut(sphere_dish)
    bot_pocket = Part.makeCylinder(12.5, 1.1, FreeCAD.Vector(0, 0, -0.1))
    tin = tin.cut(bot_pocket)
    return tin

def make_desk_jig():
    jig_len = 225.0
    jig_w = 30.0
    jig_t = 6.0
    jig = Part.makeBox(jig_w, jig_len, jig_t, FreeCAD.Vector(-jig_w/2, 0, 0))
    lip = Part.makeBox(jig_w, 10.0, 15.0, FreeCAD.Vector(-jig_w/2, 0, -15.0))
    jig = jig.fuse(lip)
    tin_cradle = Part.makeCylinder(30.2, 4.0, FreeCAD.Vector(0, 50.0 + 30.0, jig_t - 3.5))
    jig = jig.cut(tin_cradle)
    shelf_stop = Part.makeBox(jig_w + 2, 25.0, 4.0, FreeCAD.Vector(-jig_w/2 - 1, 200.0, jig_t - 3.5))
    jig = jig.cut(shelf_stop)
    # Move so resting on flat table at Z=0 (lip points up or down)
    # For printing, print flat on table with lip pointing UP:
    jig.translate(FreeCAD.Vector(0, 0, 15.0))
    return jig

def make_locking_pin():
    pin_shaft = Part.makeCylinder(1.95, 38.0, FreeCAD.Vector(0, 0, 0))
    head_base = Part.makeCylinder(4.0, 5.0, FreeCAD.Vector(0, 0, -5.0))
    ring_torus = Part.makeTorus(6.0, 2.0, FreeCAD.Vector(0, 0, -10.0), FreeCAD.Vector(0, 1, 0))
    pin_full = pin_shaft.fuse(head_base).fuse(ring_torus)
    # Lay pin horizontally flat on print bed (Z = 0)
    pin_flat = pin_full.copy()
    pin_flat.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 90)
    pin_flat.translate(FreeCAD.Vector(0, 0, 4.0))  # radius = 4mm
    return pin_flat


# ==============================================================================
# BUILD PLATE 1: 04_base_foot x 2 (좌/우 베이스 받침대 2개)
# Footprint: 120 x 200 mm (Fits easily on 220x220 bed)
# ==============================================================================
print("\n>>> Generating Plate 1: Base Feet (2pcs)...")
foot_1 = make_base_foot()
foot_1.translate(FreeCAD.Vector(-35.0, 0, 0))

foot_2 = make_base_foot()
foot_2.translate(FreeCAD.Vector(35.0, 0, 0))

plate_1 = foot_1.fuse(foot_2)
export_plate(plate_1, "Plate1_Base_Feet_x2", "베이스 받침대 2개 (좌/우 세트)")


# ==============================================================================
# BUILD PLATE 2: Columns x 4 (하부 기둥 2개 + 상부 기둥 2개 세로 수직 배치)
# Footprint: 80 x 80 mm, Height: 210 mm (Compact central layout, ready for Brim)
# ==============================================================================
print("\n>>> Generating Plate 2: Columns (4pcs)...")
# Lower Column 1 & 2
col_l1 = make_column_lower()
col_l1.translate(FreeCAD.Vector(-28.0, -28.0, 0))

col_l2 = make_column_lower()
col_l2.translate(FreeCAD.Vector(28.0, -28.0, 0))

# Upper Column 1 & 2
col_u1 = make_column_upper()
col_u1.translate(FreeCAD.Vector(-28.0, 28.0, 0))

col_u2 = make_column_upper()
col_u2.translate(FreeCAD.Vector(28.0, 28.0, 0))

plate_2 = col_l1.fuse(col_l2).fuse(col_u1).fuse(col_u2)
export_plate(plate_2, "Plate2_Columns_x4", "기둥 4개 (하부 2개 + 상부 2개)")


# ==============================================================================
# BUILD PLATE 3: Top Plate + Cross Brace (선반 상판 + 횡방향 브레이스)
# Footprint: 220 x 175 mm (Fits on 220x220 bed with brace placed parallel)
# ==============================================================================
print("\n>>> Generating Plate 3: Top Plate & Brace...")
top_plate = make_shelf_top_plate()
top_plate.translate(FreeCAD.Vector(0, -20.0, 0))

brace = make_cross_brace()
# Place brace parallel in front of plate at Y = 70
brace.translate(FreeCAD.Vector(0, 72.0, 0))

plate_3 = top_plate.fuse(brace)
export_plate(plate_3, "Plate3_TopPlate_and_Brace", "선반 상판 1개 + 횡방향 브레이스 1개")


# ==============================================================================
# BUILD PLATE 4: Tins (2pcs) + Jig (1pc) + Pins (8pcs)
# Footprint: Diagonal jig arrangement (Fits easily on 220x220 bed)
# ==============================================================================
print("\n>>> Generating Plate 4: Tins, Alignment Jig & Locking Pins...")

# 1. Desk alignment jig oriented diagonally (-45 degrees) across the bed
jig = make_desk_jig()
# Center of jig is around Y=112.5. Translate center to origin first
jig.translate(FreeCAD.Vector(0, -112.5, 0))
jig.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), -45)

# 2. ARAT Tin Cup 1 & 2 placed in opposing corner quadrants
tin_1 = make_tin_cup()
tin_1.translate(FreeCAD.Vector(-55.0, -55.0, 0))

tin_2 = make_tin_cup()
tin_2.translate(FreeCAD.Vector(55.0, 55.0, 0))

# 3. 8 Quick Locking Pins arranged neatly in 2 rows of 4 in the remaining corner
pin_plate = None
pin_proto = make_locking_pin()
# Lay out pins along X = -75 to -15, Y = 40 to 75
for ix in range(4):
    for iy in range(2):
        p = pin_proto.copy()
        p.translate(FreeCAD.Vector(-65.0 + ix*18.0, 45.0 + iy*25.0, 0))
        if pin_plate is None:
            pin_plate = p
        else:
            pin_plate = pin_plate.fuse(p)

plate_4 = jig.fuse(tin_1).fuse(tin_2).fuse(pin_plate)
export_plate(plate_4, "Plate4_Tins_Jig_Pins", "틴 2개 + 정렬 지그 1개 + 락킹 핀 8개")

print("\nAll 4 print plates generated successfully!")
