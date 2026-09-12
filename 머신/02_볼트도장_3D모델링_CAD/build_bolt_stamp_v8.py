"""
MACHINE ART LAB Bolt Stamp - v10
- Recessed nameplate, raised letters and rectangular border
- Batched local unions, nested-wire face maker, one final cleanup
- Exact collinear-point reduction; no contour smoothing or resizing
- Timestamped operations; identical single solid in all exports
Run with FreeCAD Python and the existing mirrored PNG. Dimensions in mm.
"""
import sys, os, math, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

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
print("BOLT STAMP v10 - RECESSED NAMEPLATE + FUSED EMBLEM")
print("=" * 60)
os.makedirs(output_dir, exist_ok=True)
img_path = os.path.join(output_dir, "cyborg_stamp_design_mirrored.png")
if not os.path.isfile(img_path):
    raise FileNotFoundError("Original mirrored stamp PNG required: " + img_path)

def require_solid(shape, label):
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        raise RuntimeError(label + ": expected one valid connected solid")
    return shape

started=time.perf_counter()

def log(message):
    print(f"[{time.perf_counter()-started:8.1f}s] {message}",flush=True)

def timed(label, operation):
    log(label + " START")
    t=time.perf_counter()
    result=operation()
    log(f"{label} DONE ({time.perf_counter()-t:.2f}s)")
    return result

def fuse_many(base, additions, label):
    solids=[]
    for shape in additions:
        solids.extend(shape.Solids)
    if not solids:
        return base
    # One Boolean operation, no per-component refine or full validation.
    return timed(label,lambda: base.multiFuse(solids))

doc = FreeCAD.newDocument("BoltStamp_MachineArtLab")
head_r=10.0; head_h=10.0; shank_r=7.5; total_h=45.0

# Head and shaft overlap by 0.20 mm in their final union.
# All stamp Booleans run on the head, never on a threaded full body.
log("[1/6] Simple head")
head=Part.makeCylinder(head_r,head_h)
c1=Part.makeCone(head_r+2,head_r-0.8,0.8,Base.Vector(0,0,head_h-0.8))
head=head.cut(Part.makeCylinder(head_r+2,0.8,Base.Vector(0,0,head_h-0.8)).cut(c1))

# 4. STAMP FACE: filled dark regions, preserving holes, joined into body.
log("[2/6] Stamp contours")
recess_depth=1.5
stamp_embed=0.25
head=head.cut(Part.makeCylinder(9.1,recess_depth,Base.Vector(0,0,0)))
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

def remove_collinear(poly):
    # Exact straight runs only: no resizing, smoothing or arbitrary decimation.
    p=np.asarray(poly,dtype=float)
    if len(p)>1 and np.linalg.norm(p[0]-p[-1])<1e-10:
        p=p[:-1]
    p=p[np.r_[True,np.any(np.abs(np.diff(p,axis=0))>1e-12,axis=1)]]
    if len(p)<3:
        raise RuntimeError("Degenerate artwork ring")
    previous=np.roll(p,1,axis=0)
    following=np.roll(p,-1,axis=0)
    u=p-previous; v=following-p
    cross=u[:,0]*v[:,1]-u[:,1]*v[:,0]
    straight=(np.abs(cross)<=1e-12)&(np.sum(u*v,axis=1)>0)
    result=p[~straight]
    if len(result)<3:
        raise RuntimeError("Degenerate artwork ring after straight-run reduction")
    return result

def polygon_wire(poly):
    poly=remove_collinear(poly)
    pts=[]
    for x,y in poly:
        v=Base.Vector((x-1-(w-1)/2)*scale,
                      (y-1-(h-1)/2)*scale,0)
        if not pts or (v-pts[-1]).Length>1e-8:
            pts.append(v)
    if len(pts)>1 and (pts[0]-pts[-1]).Length<1e-8:
        pts.pop()
    if len(pts)<3:
        raise RuntimeError("Degenerate artwork contour")
    pts.append(pts[0])
    return Part.Wire(Part.makePolygon(pts).Edges)

clip=Part.makeCylinder(8.9,recess_depth+stamp_embed)
# Bullseye constructs nested faces directly from closed wires, preserving
# holes and islands without incrementally fusing/cutting a growing planar shape.
log(f"  Image: {w} x {h}; rings: {len(regions)}; input points: {sum(map(len,regions))}")
wires=timed("Build contour wires",lambda: [polygon_wire(p) for p in regions])
log(f"  Reduced contour edges: {sum(len(w.Edges) for w in wires)}")
art_face=timed("Make nested artwork faces",lambda:
              Part.makeFace(wires,"Part::FaceMakerBullseye"))
if art_face.isNull() or not art_face.isValid():
    raise RuntimeError("Invalid artwork face; export cancelled")
relief=timed("Extrude and clip artwork",lambda:
    art_face.extrude(Base.Vector(0,0,recess_depth+stamp_embed)).common(clip))
if relief.isNull() or not relief.isValid():
    raise RuntimeError("Invalid stamp relief; export cancelled")
logo_solids=list(relief.Solids)
if not logo_solids:
    raise RuntimeError("No stamp solids generated; export cancelled")
artwork_count=len(logo_solids)
ring=Part.makeCylinder(8.9,recess_depth+stamp_embed).cut(
     Part.makeCylinder(8.2,recess_depth+stamp_embed))
logo_solids.append(ring)
# Positive overlap with the floor: one batched union on the simple head.
head=fuse_many(head,logo_solids,"Fuse all stamp relief to head")
head=timed("Validate stamped head",lambda: require_solid(head,"Stamped head"))

log("[3/6] Threaded shaft")
body=Part.makeCylinder(shank_r,total_h-head_h+0.20,Base.Vector(0,0,head_h-0.20))
c2=Part.makeCone(shank_r+2,shank_r-1,1,Base.Vector(0,0,total_h-1))
body=body.cut(Part.makeCylinder(shank_r+2,1,Base.Vector(0,0,total_h-1)).cut(c2))
# 2. THREADS

pitch=2.5; cuts=[]; z=12.0
while z<43.0:
    v1=Part.makeCone(shank_r+0.5,shank_r-0.65,pitch*0.5,Base.Vector(0,0,z),Base.Vector(0,0,1))
    v2=Part.makeCone(shank_r-0.65,shank_r+0.5,pitch*0.5,Base.Vector(0,0,z+pitch*0.5),Base.Vector(0,0,1))
    cs=Part.makeCylinder(shank_r+1,pitch,Base.Vector(0,0,z),Base.Vector(0,0,1))
    cuts.append(cs.cut(v1.fuse(v2))); z+=pitch
body=timed("Cut thread grooves",lambda: body.cut(Part.makeCompound(cuts)))

# 3. SOLID NAMEPLATE + RAISED TEXT
log("[4/6] Recessed nameplate and letters")
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
# Plate is built separately; its back overlaps the pocket floor.
text_raise=0.60
embed=0.20
border_width=0.55
outer=Part.makeBox(plate_w,text_raise+embed,plate_h,
                   Base.Vector(-plate_w/2,plate_top-embed,plate_z_min))
inner=Part.makeBox(plate_w-2*border_width,text_raise+embed+2,
                   plate_h-2*border_width,
                   Base.Vector(-plate_w/2+border_width,plate_top-embed-1,
                               plate_z_min+border_width))
border=outer.cut(inner)
print(f"  Inset face y={plate_top:.2f}, letters/border y={plate_top+text_raise:.2f}")

margin=0.85; gap=0.60
z_per_line=(plate_h-margin*2-gap)/2.0
# Fit each phrase separately; the shorter phrase can use larger letters.
font_size1=min(ref*z_per_line/w1,ref*(plate_w-2*margin)/h1)
font_size2=min(ref*z_per_line/w2,ref*(plate_w-2*margin)/h2)
print(f"  Fonts: MACHINE={font_size1:.2f}mm, ART LAB={font_size2:.2f}mm")

mat=FreeCAD.Matrix()
mat.A11=0;mat.A12=1;mat.A13=0;mat.A14=0
mat.A21=0;mat.A22=0;mat.A23=1;mat.A24=0
mat.A31=1;mat.A32=0;mat.A33=0;mat.A34=0



ss1=Draft.make_shapestring(String="MACHINE",FontFile=font_path,Size=font_size1)
doc.recompute()
t1o=ss1.Shape.extrude(Base.Vector(0,0,text_raise+embed))
t1o.transformShape(mat)
bb1=t1o.BoundBox
l1z=plate_z_min+margin+z_per_line/2
t1o.translate(Base.Vector(-(bb1.XMin+bb1.XMax)/2, plate_top-embed-bb1.YMin, l1z-(bb1.ZMin+bb1.ZMax)/2))
doc.removeObject(ss1.Name)

ss2=Draft.make_shapestring(String="ART LAB",FontFile=font_path,Size=font_size2)
doc.recompute()
t2o=ss2.Shape.extrude(Base.Vector(0,0,text_raise+embed))
t2o.transformShape(mat)
bb2=t2o.BoundBox
l2z=plate_z_max-margin-z_per_line/2
t2o.translate(Base.Vector(-(bb2.XMin+bb2.XMax)/2, plate_top-embed-bb2.YMin, l2z-(bb2.ZMin+bb2.ZMax)/2))
doc.removeObject(ss2.Name)

nameplate=fuse_many(plate,[border,t1o,t2o],"Fuse nameplate locally")
body=fuse_many(body,[nameplate],"Attach nameplate to shaft")
print(f"  Text: {text_raise}mm raised above plate")


log("[5/6] Final union")
final=fuse_many(head,[body],"Join stamped head and finished shaft")
# Refine exactly once, after the final Boolean operation.
final=timed("Final face cleanup",lambda: final.removeSplitter())
final=timed("Final solid validation",lambda: require_solid(final,"Final model"))
log(f"Artwork solids: {artwork_count}; final solids: {len(final.Solids)}")

# 5. EXPORT THE SAME SINGLE SOLID IN EVERY FORMAT.
log("[6/6] Exporting and checking")
for o in list(doc.Objects):
    doc.removeObject(o.Name)
feat=doc.addObject("Part::Feature","Bolt_Stamp_MachineArtLab")
feat.Shape=final
doc.recompute()
base_path=os.path.join(output_dir,"Bolt_Stamp_MachineArtLab_v10")
fcstd=base_path+".FCStd"
step_f=base_path+".step"
stl_f=base_path+".stl"
mesh=timed("Mesh final solid",lambda: MeshPart.meshFromShape(
    Shape=final,LinearDeflection=0.02,AngularDeflection=0.15,Relative=False))
if mesh.CountFacets==0 or not mesh.isSolid():
    raise RuntimeError("STL mesh is not closed; export cancelled")
timed("Save FCStd",lambda: doc.saveAs(fcstd))
timed("Save STEP",lambda: Part.export([feat],step_f))
timed("Save STL",lambda: mesh.write(stl_f))
# Reload actual exports; reject disconnected or non-closed outputs.
check=Part.Shape()
timed("Reload STEP",lambda: check.read(step_f))
timed("Validate reloaded STEP",lambda: require_solid(check,"Reloaded STEP"))
if abs(check.Volume-final.Volume)>max(1e-5,final.Volume*1e-6):
    raise RuntimeError("STEP volume differs from final model")
import Mesh
stl_check=timed("Reload STL",lambda: Mesh.Mesh(stl_f))
if not stl_check.isSolid():
    raise RuntimeError("Reloaded STL is not closed")
if abs(abs(stl_check.Volume)-final.Volume)>final.Volume*0.01:
    raise RuntimeError("STL volume differs by more than 1%")
# Diagnostic only: exact CAD sections, not a prediction of nozzle toolpaths.
# At z=0.10 the artwork should be present; z=1.60 crosses the backing floor.
def save_stamp_sections():
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    axes[0].imshow(np.flipud(arr),cmap="gray",vmin=0,vmax=255)
    axes[0].set_title("Source PNG (already mirrored)")
    axes[0].axis("off")
    for ax,z_level in zip(axes[1:],(0.10,1.60)):
        plane=Part.makePlane(24,24,Base.Vector(-12,-12,z_level))
        section=final.section(plane)
        if not section.Edges:
            raise RuntimeError(f"No CAD section at z={z_level}")
        for edge in section.Edges:
            points=edge.discretize(Deflection=0.02)
            ax.plot([pt.x for pt in points],[pt.y for pt in points],"k-",linewidth=0.7)
        ax.set_aspect("equal")
        ax.set_xlim(-10.5,10.5); ax.set_ylim(-10.5,10.5)
        ax.set_title(f"CAD section z={z_level:.2f} mm")
        ax.set_xlabel("X (mm)"); ax.set_ylabel("Y (mm)")
    fig.tight_layout()
    target=base_path+"_stamp_sections.png"
    fig.savefig(target,dpi=180)
    plt.close(fig)
    log("Diagnostic image: " + target)
try:
    timed("Stamp cross-section diagnostic",save_stamp_sections)
except Exception as exc:
    # Diagnostics must not invalidate already checked CAD exports.
    log("Diagnostic image failed (CAD exports completed): " + str(exc))

if FreeCAD.GuiUp:
    import FreeCADGui
    FreeCADGui.activeDocument().activeView().viewAxonometric()
    FreeCADGui.activeDocument().activeView().fitAll()
log("v10 DONE - one fused solid, STEP/STL reloaded successfully")
print(f"  STL triangles: {mesh.CountFacets}")
for path in (fcstd,step_f,stl_f):
    print(f"  {path}: {os.path.getsize(path):,} bytes")
