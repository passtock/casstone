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
PLATES_DIR = os.path.join(KIT_DIR, "print_plates")
os.makedirs(PLATES_DIR, exist_ok=True)

TOL = 0.25

def export_plate(shape, filename_base, desc=""):
    step_file = os.path.join(PLATES_DIR, f"{filename_base}.step")
    stl_file = os.path.join(PLATES_DIR, f"{filename_base}.stl")
    
    shape.exportStep(step_file)
    mesh = MeshPart.meshFromShape(shape, LinearDeflection=0.08, AngularDeflection=0.25)
    mesh.removeDuplicatedPoints()
    mesh.removeDuplicatedFacets()
    mesh.fixIndices()
    mesh.write(stl_file)
    
    bbox = shape.BoundBox
    print(f"\n========================================================")
    print(f"[PLATE READY v3] {filename_base}.stl  ({desc})")
    print(f"  Footprint: X [{bbox.XMin:5.1f} ~ {bbox.XMax:5.1f}] ({bbox.XLength:5.1f} mm)")
    print(f"             Y [{bbox.YMin:5.1f} ~ {bbox.YMax:5.1f}] ({bbox.YLength:5.1f} mm)")
    print(f"             Z [{bbox.ZMin:5.1f} ~ {bbox.ZMax:5.1f}] ({bbox.ZLength:5.1f} mm)")
    print(f"  File size: STL {os.path.getsize(stl_file)/1024:6.1f} KB | STEP {os.path.getsize(step_file)/1024:6.1f} KB")
    print(f"========================================================")

# ==============================================================================
# Helper functions for updated v3 parts
# ==============================================================================
def make_base_foot():
    foot_len = 200.0
    foot_w = 55.0
    foot_h = 30.0
    foot = Part.makeBox(foot_w, foot_len, 12.0, FreeCAD.Vector(-foot_w/2, -foot_len/2, 0))
    collar = Part.makeBox(48.0, 48.0, 18.0, FreeCAD.Vector(-24.0, -24.0, 12.0))
    foot = foot.fuse(collar)
    col_cav_w = 30.0 + 2*TOL
    col_cavity = Part.makeBox(col_cav_w, col_cav_w, 25.2, FreeCAD.Vector(-col_cav_w/2, -col_cav_w/2, 5.0))
    foot = foot.cut(col_cavity)
    pin_collar = Part.makeCylinder(2.1, 60.0, FreeCAD.Vector(-30.0, 0, 17.5), FreeCAD.Vector(1, 0, 0))
    foot = foot.cut(pin_collar)
    for sy in [-70.0, 70.0]:
        scr = Part.makeCylinder(2.25, 20.0, FreeCAD.Vector(0, sy, -1.0))
        cb = Part.makeCylinder(4.5, 6.0, FreeCAD.Vector(0, sy, 7.0))
        foot = foot.cut(scr).cut(cb)
    aruco_pocket = Part.makeBox(1.5, 40.0, 20.0, FreeCAD.Vector(foot_w/2 - 1.0, -20.0, 7.0))
    foot = foot.cut(aruco_pocket)
    for y_pad in [-85.0, -40.0, 40.0, 85.0]:
        pad_pocket = Part.makeCylinder(6.0, 1.6, FreeCAD.Vector(0, y_pad, -0.1))
        foot = foot.cut(pad_pocket)
    return foot

def make_column_lower():
    col_l_body = Part.makeBox(30.0, 30.0, 175.0, FreeCAD.Vector(-15.0, -15.0, 0))
    tenon_top = Part.makeBox(20.0, 20.0, 25.0, FreeCAD.Vector(-10.0, -10.0, 175.0))
    col_l = col_l_body.fuse(tenon_top)
    pin_bot = Part.makeCylinder(2.0, 40.0, FreeCAD.Vector(-20.0, 0, 12.5), FreeCAD.Vector(1, 0, 0))
    col_l = col_l.cut(pin_bot)
    pin_top = Part.makeCylinder(2.0, 30.0, FreeCAD.Vector(-15.0, 0, 190.0), FreeCAD.Vector(1, 0, 0))
    col_l = col_l.cut(pin_top)
    brace_mortise = Part.makeBox(10.1, 15.0 + 2*TOL, 25.0 + 2*TOL, FreeCAD.Vector(5.0, -(15.0 + 2*TOL)/2, 90.0 - (25.0 + 2*TOL)/2))
    col_l = col_l.cut(brace_mortise)
    brace_pin = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(0, -20.0, 90.0), FreeCAD.Vector(0, 1, 0))
    col_l = col_l.cut(brace_pin)
    return col_l

def make_column_upper():
    col_u_body = Part.makeBox(30.0, 30.0, 170.0, FreeCAD.Vector(-15.0, -15.0, 0))
    cav_tenon_w = 20.0 + 2*TOL
    cav_bot = Part.makeBox(cav_tenon_w, cav_tenon_w, 26.0, FreeCAD.Vector(-cav_tenon_w/2, -cav_tenon_w/2, -0.1))
    col_u = col_u_body.cut(cav_bot)
    tenon_top_u = Part.makeBox(20.0, 20.0, 13.0, FreeCAD.Vector(-10.0, -10.0, 170.0))
    col_u = col_u_body.fuse(tenon_top_u)
    pin_bot_u = Part.makeCylinder(2.1, 40.0, FreeCAD.Vector(-20.0, 0, 10.0), FreeCAD.Vector(1, 0, 0))
    col_u = col_u.cut(pin_bot_u)
    pin_top_u = Part.makeCylinder(2.0, 30.0, FreeCAD.Vector(-15.0, 0, 176.0), FreeCAD.Vector(1, 0, 0))
    col_u = col_u.cut(pin_top_u)
    return col_u

def make_shelf_top_plate():
    plate_w = 220.0
    plate_d = 150.0
    plate_t = 10.0
    plate = Part.makeBox(plate_w, plate_d, plate_t, FreeCAD.Vector(-plate_w/2, -plate_d/2, 0))
    for tx in [-55.0, 55.0]:
        t_pocket = Part.makeCylinder(46.0, 2.6, FreeCAD.Vector(tx, -29.0, plate_t - 2.5))
        plate = plate.cut(t_pocket)
    for mx in [-90.0, 90.0]:
        for my in [-55.0, 55.0]:
            screw_hole = Part.makeCylinder(2.2, plate_t + 2.0, FreeCAD.Vector(mx, my, -1.0))
            cbore = Part.makeCylinder(4.2, 5.0, FreeCAD.Vector(mx, my, plate_t - 4.5))
            plate = plate.cut(screw_hole).cut(cbore)
    for sx in [-70.0, 70.0]:
        boss = Part.makeBox(40.0, 40.0, 10.0, FreeCAD.Vector(sx - 20.0, -20.0, -10.0))
        plate = plate.fuse(boss)
    for sx in [-70.0, 70.0]:
        cav_w = 20.0 + 2*TOL
        cavity = Part.makeBox(cav_w, cav_w, 15.2, FreeCAD.Vector(sx - cav_w/2, -cav_w/2, -10.1))
        plate = plate.cut(cavity)
        pin_hole = Part.makeCylinder(2.1, 45.0, FreeCAD.Vector(sx - 22.5, 0, -4.0), FreeCAD.Vector(1, 0, 0))
        plate = plate.cut(pin_hole)
    plate.translate(FreeCAD.Vector(0, 0, 10.0))
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
    tin_od = 90.0
    tin_id = 85.0
    tin_rim_h = 10.0
    tin_floor = 2.5
    tin_total_h = tin_floor + tin_rim_h
    tin_outer = Part.makeCylinder(tin_od/2, tin_total_h, FreeCAD.Vector(0, 0, 0))
    tin_inner = Part.makeCylinder(tin_id/2, tin_rim_h + 1.0, FreeCAD.Vector(0, 0, tin_floor))
    tin = tin_outer.cut(tin_inner)
    dish_r = 150.0
    dish_center_z = tin_floor + dish_r - 1.2
    dish = Part.makeSphere(dish_r, FreeCAD.Vector(0, 0, dish_center_z))
    tin = tin.cut(dish)
    pocket_bot = Part.makeCylinder(17.5, 1.0, FreeCAD.Vector(0, 0, -0.1))
    tin = tin.cut(pocket_bot)
    return tin

def make_desk_jig():
    jig_len = 225.0
    jig_w = 30.0
    jig_t = 6.0
    jig = Part.makeBox(jig_w, jig_len, jig_t, FreeCAD.Vector(-jig_w/2, 0, 0))
    lip = Part.makeBox(jig_w, 10.0, 15.0, FreeCAD.Vector(-jig_w/2, 0, -15.0))
    jig = jig.fuse(lip)
    tin_cradle = Part.makeCylinder(45.2, 4.0, FreeCAD.Vector(0, 95.0, jig_t - 3.5))
    jig = jig.cut(tin_cradle)
    shelf_stop = Part.makeBox(jig_w + 2, 30.0, 4.0, FreeCAD.Vector(-jig_w/2 - 1, 200.0, jig_t - 3.5))
    jig = jig.cut(shelf_stop)
    jig.translate(FreeCAD.Vector(0, 0, 15.0))
    return jig

def make_locking_pin():
    pin_shaft = Part.makeCylinder(1.95, 38.0, FreeCAD.Vector(0, 0, 0))
    head_base = Part.makeCylinder(4.0, 5.0, FreeCAD.Vector(0, 0, -5.0))
    ring_torus = Part.makeTorus(6.0, 2.0, FreeCAD.Vector(0, 0, -10.0), FreeCAD.Vector(0, 1, 0))
    pin_full = pin_shaft.fuse(head_base).fuse(ring_torus)
    pin_flat = pin_full.copy()
    pin_flat.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0), 90)
    pin_flat.translate(FreeCAD.Vector(0, 0, 4.0))
    return pin_flat


# ==============================================================================
# BUILD PLATE 1: Base Feet x 2
# ==============================================================================
print("\n>>> Generating Plate 1: Base Feet (2pcs)...")
foot_1 = make_base_foot()
foot_1.translate(FreeCAD.Vector(-35.0, 0, 0))

foot_2 = make_base_foot()
foot_2.translate(FreeCAD.Vector(35.0, 0, 0))

plate_1 = foot_1.fuse(foot_2)
export_plate(plate_1, "Plate1_Base_Feet_x2", "베이스 받침대 2개 (좌/우 세트, 클램프 고정 립 & ArUco 홈 포함)")


# ==============================================================================
# BUILD PLATE 2: Columns x 4
# ==============================================================================
print("\n>>> Generating Plate 2: Columns (4pcs)...")
col_l1 = make_column_lower()
col_l1.translate(FreeCAD.Vector(-28.0, -28.0, 0))

col_l2 = make_column_lower()
col_l2.translate(FreeCAD.Vector(28.0, -28.0, 0))

col_u1 = make_column_upper()
col_u1.translate(FreeCAD.Vector(-28.0, 28.0, 0))

col_u2 = make_column_upper()
col_u2.translate(FreeCAD.Vector(28.0, 28.0, 0))

plate_2 = col_l1.fuse(col_l2).fuse(col_u1).fuse(col_u2)
export_plate(plate_2, "Plate2_Columns_x4", "기둥 4개 (하부 2개 + 상부 2개, 매끈한 플러시 결합)")


# ==============================================================================
# BUILD PLATE 3: Top Plate (220x150mm) + Cross Brace
# Fits directly on 220x220 mm beds!
# ==============================================================================
print("\n>>> Generating Plate 3: Top Plate & Brace...")
top_plate = make_shelf_top_plate()
top_plate.translate(FreeCAD.Vector(0, -20.0, 0))

brace = make_cross_brace()
brace.translate(FreeCAD.Vector(0, 75.0, 0))

plate_3 = top_plate.fuse(brace)
export_plate(plate_3, "Plate3_TopPlate_and_Brace", "좌우 양손 대칭 선반 상판(220x150mm) + 횡방향 브레이스")


# ==============================================================================
# BUILD PLATE 4: Standard dia 90mm Tins (x2) + Desk Jig + 8 Pins
# Optimized layout fits 208 x 206 mm (comfortably inside ANY 220x220 bed)
# ==============================================================================
print("\n>>> Generating Plate 4: Tins (dia 90mm x2), Alignment Jig & Locking Pins...")

jig = make_desk_jig()
jig.translate(FreeCAD.Vector(0, -112.5, 0))
jig.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), -45)

tin_1 = make_tin_cup()
tin_1.translate(FreeCAD.Vector(-58.0, 58.0, 0))

tin_2 = make_tin_cup()
tin_2.translate(FreeCAD.Vector(58.0, -58.0, 0))

pin_proto = make_locking_pin()
pins_fused = None
for i in range(4):
    p1 = pin_proto.copy()
    p1.translate(FreeCAD.Vector(-95.0 + i*14.0, -40.0, 0))
    p2 = pin_proto.copy()
    p2.translate(FreeCAD.Vector(55.0 + i*14.0, 10.0, 0))
    p_pair = p1.fuse(p2)
    if pins_fused is None:
        pins_fused = p_pair
    else:
        pins_fused = pins_fused.fuse(p_pair)

plate_4 = jig.fuse(tin_1).fuse(tin_2).fuse(pins_fused)
export_plate(plate_4, "Plate4_Tins_Jig_Pins", "표준 dia 90mm 틴 2개 (깊이 10mm) + 셋업 지그 + 락킹 핀 8개")

print("\nAll updated 4 print plates v3 generated successfully!")
