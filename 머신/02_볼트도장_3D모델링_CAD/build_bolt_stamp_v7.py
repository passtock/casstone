"""
MACHINE ART LAB Bolt Stamp - v8
- Recessed nameplate, raised letters and rectangular border
- Stamp relief fused into one solid; identical geometry in all exports
Run with FreeCAD Python and the existing mirrored PNG. Dimensions in mm.
"""
import sys, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageFilter

freecad_bin = r"C:\Program Files\FreeCAD 1.1\bin"
freecad_mod = r"C:\Program Files\FreeCAD 1.1\Mod"
for p in [freecad_bin, freecad_mod]:
    if p not in sys.path:
        sys.path.insert(0, p)

import FreeCAD
import Part
from FreeCAD import Base
import Draft
import MeshPart

output_dir = r"c:\Users\passp\Desktop\univercity\4-2\캡스톤\머신\02_볼트도장_3D모델링_CAD"

print("=" * 60)
print("BOLT STAMP v8 - RECESSED NAMEPLATE + FUSED EMBLEM")
print("=" * 60)
os.makedirs(output_dir, exist_ok=True)
img_path = os.path.join(output_dir, "cyborg_stamp_design_mirrored.png")
if not os.path.isfile(img_path):
    raise FileNotFoundError("Original mirrored stamp PNG required: " + img_path)

def require_solid(shape, label):
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        raise RuntimeError(label + ": expected one valid connected solid")
    return shape

def join(base, addition, label):
    result = base.fuse(addition).removeSplitter()
    return require_solid(result, label)

doc = FreeCAD.newDocument("BoltStamp_MachineArtLab")
head_r=10.0; head_h=10.0; shank_r=7.5; total_h=45.0

# 1. BOLT BODY
print("[1/5] Body...")
body = Part.makeCylinder(head_r,head_h,Base.Vector(0,0,0),Base.Vector(0,0,1)).fuse(
       Part.makeCylinder(shank_r,total_h-head_h,Base.Vector(0,0,head_h),Base.Vector(0,0,1)))
c1=Part.makeCone(head_r+2,head_r-0.8,0.8,Base.Vector(0,0,head_h-0.8),Base.Vector(0,0,1))
body=body.cut(Part.makeCylinder(head_r+2,0.8,Base.Vector(0,0,head_h-0.8),Base.Vector(0,0,1)).cut(c1))
c2=Part.makeCone(shank_r+2,shank_r-1,1,Base.Vector(0,0,total_h-1),Base.Vector(0,0,1))
body=body.cut(Part.makeCylinder(shank_r+2,1,Base.Vector(0,0,total_h-1),Base.Vector(0,0,1)).cut(c2))

# 2. THREADS
print("[2/5] Threads...")
pitch=2.5; cuts=[]; z=12.0
while z<43.0:
    v1=Part.makeCone(shank_r+0.5,shank_r-0.65,pitch*0.5,Base.Vector(0,0,z),Base.Vector(0,0,1))
    v2=Part.makeCone(shank_r-0.65,shank_r+0.5,pitch*0.5,Base.Vector(0,0,z+pitch*0.5),Base.Vector(0,0,1))
    cs=Part.makeCylinder(shank_r+1,pitch,Base.Vector(0,0,z),Base.Vector(0,0,1))
    cuts.append(cs.cut(v1.fuse(v2))); z+=pitch
body=body.cut(Part.makeCompound(cuts))

# 3. SOLID NAMEPLATE + RAISED TEXT
print("[3/5] Solid nameplate + text...")
font_path=r"C:\Windows\Fonts\arialbd.ttf"
ref=10.0
ss1r=Draft.make_shapestring(String="MACHINE",FontFile=font_path,Size=ref)
doc.recompute(); w1=ss1r.Shape.BoundBox.XLength; h1=ss1r.Shape.BoundBox.YLength
doc.removeObject(ss1r.Name)
ss2r=Draft.make_shapestring(String="ART LAB",FontFile=font_path,Size=ref)
doc.recompute(); w2=ss2r.Shape.BoundBox.XLength; h2=ss2r.Shape.BoundBox.YLength
doc.removeObject(ss2r.Name)

plate_w=10.0; plate_h=31.0; plate_thick=1.2
plate_z_min=11.5; plate_z_max=plate_z_min+plate_h
# The full rectangle is inside the thread root envelope, even at its corners.
# Root radius = 6.85; at x=+/-5 its surface y is about 4.68 mm.
plate_top=4.35
plate_y=plate_top-plate_thick
body=body.cut(Part.makeBox(plate_w, head_r+2-plate_top, plate_h,
                          Base.Vector(-plate_w/2,plate_top,plate_z_min)))
plate=Part.makeBox(plate_w,plate_thick,plate_h,
                   Base.Vector(-plate_w/2,plate_y,plate_z_min))
body=join(body,plate,"Recessed nameplate")
text_raise=0.60
embed=0.20
border_width=0.55
outer=Part.makeBox(plate_w,text_raise+embed,plate_h,
                   Base.Vector(-plate_w/2,plate_top-embed,plate_z_min))
inner=Part.makeBox(plate_w-2*border_width,text_raise+embed+2,
                   plate_h-2*border_width,
                   Base.Vector(-plate_w/2+border_width,plate_top-embed-1,
                               plate_z_min+border_width))
body=join(body,outer.cut(inner),"Raised rectangular border")
print(f"  Inset face y={plate_top:.2f}, letters/border y={plate_top+text_raise:.2f}")

margin=1.0; gap=2.0
z_per_line=(plate_h-margin*2-gap)/2.0
font_size=min(ref*(z_per_line/max(w1,w2)), ref*((plate_w-margin*2)/max(h1,h2)))
print(f"  Font: {font_size:.2f}mm")

mat=FreeCAD.Matrix()
mat.A11=0;mat.A12=1;mat.A13=0;mat.A14=0
mat.A21=0;mat.A22=0;mat.A23=1;mat.A24=0
mat.A31=1;mat.A32=0;mat.A33=0;mat.A34=0



ss1=Draft.make_shapestring(String="MACHINE",FontFile=font_path,Size=font_size)
doc.recompute()
t1o=ss1.Shape.extrude(Base.Vector(0,0,text_raise+embed))
t1o.transformShape(mat)
bb1=t1o.BoundBox
l1z=plate_z_min+margin+z_per_line/2
t1o.translate(Base.Vector(-(bb1.XMin+bb1.XMax)/2, plate_top-embed-bb1.YMin, l1z-(bb1.ZMin+bb1.ZMax)/2))
doc.removeObject(ss1.Name)

ss2=Draft.make_shapestring(String="ART LAB",FontFile=font_path,Size=font_size)
doc.recompute()
t2o=ss2.Shape.extrude(Base.Vector(0,0,text_raise+embed))
t2o.transformShape(mat)
bb2=t2o.BoundBox
l2z=plate_z_max-margin-z_per_line/2
t2o.translate(Base.Vector(-(bb2.XMin+bb2.XMax)/2, plate_top-embed-bb2.YMin, l2z-(bb2.ZMin+bb2.ZMax)/2))
doc.removeObject(ss2.Name)

body=join(body,t1o,"MACHINE letters")
body=join(body,t2o,"ART LAB letters")
print(f"  Text: {text_raise}mm raised above plate")

# 4. STAMP FACE: filled dark regions, preserving holes, joined into body.
print("[4/5] Stamp emblem (fused relief)...")
recess_depth=1.5
stamp_embed=0.25
body=body.cut(Part.makeCylinder(9.1,recess_depth,Base.Vector(0,0,0)))
# This PNG is already mirrored. Do not mirror it a second time.
# Composite transparency on white; transparent black pixels must not become ink.
rgba=Image.open(img_path).convert("RGBA")
white=Image.new("RGBA",rgba.size,(255,255,255,255))
white.alpha_composite(rgba)
im=white.convert("L")
# No minimum filter: preserve thin holes and the original artwork.
arr=np.asarray(im,dtype=float)
h,w=arr.shape
if min(w,h)<2 or not np.any(arr<128) or not np.any(arr>=128):
    raise RuntimeError("Stamp PNG must contain dark artwork on a light background")
# White padding closes artwork touching the image boundary.
arr=np.pad(np.flipud(arr),1,constant_values=255)
scale=18.0/max(w,h)
fig,ax=plt.subplots()
cs=ax.contourf(arr,levels=[-1,128])
# allsegs/allkinds preserve each filled component and its interior rings.
from matplotlib.path import Path as MplPath
regions=[]
for vertices,codes in zip(cs.allsegs[0],cs.allkinds[0]):
    regions.extend(MplPath(vertices,codes).to_polygons(closed_only=True))
plt.close(fig)

def rdp(points, epsilon):
    """Ramer-Douglas-Peucker 2D polygon simplification"""
    if len(points) < 3: return points
    p1 = points[0]; p2 = points[-1]; line_vec = p2 - p1
    line_len = np.linalg.norm(line_vec)
    if line_len < 1e-8:
        d = np.linalg.norm(points - p1, axis=1)
    else:
        norm_vec = np.array([-line_vec[1], line_vec[0]]) / line_len
        d = np.abs(np.dot(points - p1, norm_vec))
    index = np.argmax(d)
    if d[index] > epsilon:
        rec1 = rdp(points[:index+1], epsilon)
        rec2 = rdp(points[index:], epsilon)
        return np.vstack((rec1[:-1], rec2))
    return np.vstack((points[0], points[-1]))

def signed_area(poly):
    return 0.5*float(np.sum(poly[:,0]*np.roll(poly[:,1],-1)
                            - np.roll(poly[:,0],-1)*poly[:,1]))

cx = (w - 1) / 2
cy = (h - 1) / 2
max_r_pixel = 8.15 / scale  # Emblem inside the 8.2mm circular ring

outers = []; holes = []
for p in regions:
    pts_x = p[:, 0] - 1 - cx
    pts_y = p[:, 1] - 1 - cy
    if np.max(np.sqrt(pts_x**2 + pts_y**2)) < max_r_pixel:
        area = signed_area(p)
        if abs(area) < 4.0: continue  # filter sub-pixel noise
        sim_p = rdp(p, epsilon=0.5)   # 0.5 pixel precision (~0.018mm)
        if len(sim_p) < 4: continue
        sim_area = signed_area(sim_p)
        if sim_area > 0:
            outers.append((sim_area, sim_p))
        else:
            holes.append((sim_area, sim_p))

outers.sort(key=lambda x: x[0], reverse=True)
outer_paths = [MplPath(p) for _, p in outers]
holes_assigned = [[] for _ in outers]
for h_area, h_poly in holes:
    pt = h_poly[0]
    for i in reversed(range(len(outers))):
        if outer_paths[i].contains_point(pt):
            holes_assigned[i].append(h_poly)
            break

def make_wire(poly):
    pts = []
    for x, y in poly:
        v = Base.Vector((x-1-cx)*scale, (y-1-cy)*scale, 0)
        if not pts or (v - pts[-1]).Length > 1e-6:
            pts.append(v)
    if len(pts) > 1 and (pts[0] - pts[-1]).Length < 1e-6:
        pts.pop()
    if len(pts) < 3: return None
    pts.append(pts[0])
    return Part.makePolygon(pts)

clip = Part.makeCylinder(8.9, recess_depth+stamp_embed)
faces = []
for i, (_, o_poly) in enumerate(outers):
    w_out = make_wire(o_poly)
    if not w_out: continue
    hole_wires = [make_wire(hp) for hp in holes_assigned[i] if make_wire(hp)]
    try:
        f = Part.Face([w_out] + hole_wires) if hole_wires else Part.Face(w_out)
        if f.isValid(): faces.append(f)
    except:
        try:
            f = Part.Face(w_out)
            if f.isValid(): faces.append(f)
        except: pass

logo_solids = [f.extrude(Base.Vector(0,0,recess_depth+stamp_embed)).common(clip)
               for f in faces if f.isValid()]
logo_solids = [s for s in logo_solids if s.isValid() and not s.isNull()]
artwork_count = len(logo_solids)

ring = Part.makeCylinder(8.9, recess_depth+stamp_embed).cut(
       Part.makeCylinder(8.2, recess_depth+stamp_embed))
logo_solids.append(ring)

# Single compound fusion directly into body
body = join(body, Part.makeCompound(logo_solids), "Stamp emblem relief")
final = require_solid(body.removeSplitter(), "Final model")
print(f"  Fused artwork components: {artwork_count}; final solids: {len(final.Solids)}")

# 5. EXPORT THE SAME SINGLE SOLID IN EVERY FORMAT.
print("[5/5] Exporting and checking...")
for o in list(doc.Objects):
    doc.removeObject(o.Name)
feat=doc.addObject("Part::Feature","Bolt_Stamp_MachineArtLab")
feat.Shape=final
doc.recompute()
base_path=os.path.join(output_dir,"Bolt_Stamp_MachineArtLab_v8")
fcstd=base_path+".FCStd"
step_f=base_path+".step"
stl_f=base_path+".stl"
mesh=MeshPart.meshFromShape(Shape=final,LinearDeflection=0.02,
                           AngularDeflection=0.15,Relative=False)
if mesh.CountFacets==0 or not mesh.isSolid():
    raise RuntimeError("STL mesh is not closed; export cancelled")
doc.saveAs(fcstd)
Part.export([feat],step_f)
mesh.write(stl_f)
# Reload actual exports; reject disconnected or non-closed outputs.
check=Part.Shape()
check.read(step_f)
require_solid(check,"Reloaded STEP")
if abs(check.Volume-final.Volume)>max(1e-5,final.Volume*1e-6):
    raise RuntimeError("STEP volume differs from final model")
import Mesh
stl_check=Mesh.Mesh(stl_f)
if not stl_check.isSolid():
    raise RuntimeError("Reloaded STL is not closed")
if abs(abs(stl_check.Volume)-final.Volume)>final.Volume*0.01:
    raise RuntimeError("STL volume differs by more than 1%")
if FreeCAD.GuiUp:
    import FreeCADGui
    FreeCADGui.activeDocument().activeView().viewAxonometric()
    FreeCADGui.activeDocument().activeView().fitAll()
print("\nv8 DONE -- one fused solid, STEP/STL reloaded successfully")
print(f"  STL triangles: {mesh.CountFacets}")
for path in (fcstd,step_f,stl_f):
    print(f"  {path}: {os.path.getsize(path):,} bytes")
