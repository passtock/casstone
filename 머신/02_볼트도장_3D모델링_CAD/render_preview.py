import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image

output_dir = r"c:\Users\passp\Desktop\univercity\4-2\캡스톤\머신\02_볼트도장_3D모델링_CAD"
stl_path = os.path.join(output_dir, "Bolt_Stamp_MachineArtLab_v10.stl")
save_path = os.path.join(output_dir, "Bolt_Stamp_3D_Preview_v10.png")

print("Rendering 3D preview views from STL...")

def load_stl_binary(filepath):
    with open(filepath, 'rb') as f:
        header = f.read(80)
        num_triangles = int.from_bytes(f.read(4), byteorder='little')
        print(f"Loading {num_triangles} triangles from {os.path.basename(filepath)}...")
        
        # Read all triangle records: 50 bytes each (12 floats + 2 bytes attribute)
        # 12 floats = 3 normal, 3 v1, 3 v2, 3 v3
        dt = np.dtype([
            ('normal', '<f4', (3,)),
            ('v1', '<f4', (3,)),
            ('v2', '<f4', (3,)),
            ('v3', '<f4', (3,)),
            ('attr', '<u2')
        ])
        data = np.fromfile(f, dtype=dt, count=num_triangles)
        
        # Vertices shape: (num_triangles, 3, 3)
        v = np.stack([data['v1'], data['v2'], data['v3']], axis=1)
        return v

# Check if STL is ready
if os.path.exists(stl_path):
    verts = load_stl_binary(stl_path)
    total_tri = len(verts)
    print(f"Total triangles: {total_tri}")

    # Subsample for smooth 3D plotting if triangle count is high
    max_tri = 18000
    if total_tri > max_tri:
        step = total_tri // max_tri
        sub_verts = verts[::step]
    else:
        sub_verts = verts

    # 1. Multi-view Figure (2x2 Grid)
    fig = plt.figure(figsize=(16, 16), facecolor="#14171c")

    # View 1: Isometric View
    ax1 = fig.add_subplot(2, 2, 1, projection='3d', facecolor="#14171c")
    mesh1 = Poly3DCollection(sub_verts, alpha=0.92, edgecolor='#2c323d', linewidth=0.1)
    mesh1.set_facecolor('#8fa0b5')
    ax1.add_collection3d(mesh1)
    ax1.set_title("Machine Art Lab Bolt Stamp - Isometric View", color='white', fontsize=14, pad=12, fontweight='bold')
    ax1.view_init(elev=25, azim=45)

    # View 2: Side View (Typo Plate & Screw Threads)
    ax2 = fig.add_subplot(2, 2, 2, projection='3d', facecolor="#14171c")
    mesh2 = Poly3DCollection(sub_verts, alpha=0.92, edgecolor='#2c323d', linewidth=0.1)
    mesh2.set_facecolor('#a4b8cc')
    ax2.add_collection3d(mesh2)
    ax2.set_title("Side View: Nameplate Pocket ('MACHINE ART LAB')", color='white', fontsize=14, pad=12, fontweight='bold')
    ax2.view_init(elev=10, azim=85)

    # View 3: Stamp Face (Bottom View of Head - Mirrored Relief)
    ax3 = fig.add_subplot(2, 2, 3, projection='3d', facecolor="#14171c")
    # Filter vertices near stamp face (Z <= 2.0 mm)
    face_mask = (sub_verts[:, :, 2].max(axis=1) <= 2.5)
    face_verts = sub_verts[face_mask]
    mesh3 = Poly3DCollection(face_verts, alpha=0.95, edgecolor='#242b35', linewidth=0.15)
    mesh3.set_facecolor('#dce6f2')
    ax3.add_collection3d(mesh3)
    ax3.set_title("Stamp Head Face (Bottom 3D Relief - Mirrored for Stamping)", color='white', fontsize=14, pad=12, fontweight='bold')
    ax3.view_init(elev=-90, azim=0) # Look directly from bottom up

    # Set limits for all 3D axes
    for ax, lim in [(ax1, 24), (ax2, 24), (ax3, 12)]:
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        if ax != ax3:
            ax.set_zlim(-3, 47)
        else:
            ax.set_zlim(-3, 5)
        ax.set_axis_off()

    # View 4: 2D Stamped Ink Simulation (What it looks like stamped on paper)
    ax4 = fig.add_subplot(2, 2, 4, facecolor="#f5f5f7")
    stamp_img_path = os.path.join(output_dir, "cyborg_stamp_design_normal.png")
    if os.path.exists(stamp_img_path):
        st_im = Image.open(stamp_img_path)
        # Colorize to stamp ink (deep vermilion / seal red)
        arr = np.array(st_im.convert("L"))
        ink = np.ones((arr.shape[0], arr.shape[1], 4), dtype=np.uint8) * 255
        ink[..., 0] = 195  # Red
        ink[..., 1] = 30   # Green
        ink[..., 2] = 25   # Blue
        ink[..., 3] = np.where(arr < 128, 230, 0).astype(np.uint8) # Alpha
        ax4.imshow(ink)
    ax4.set_title("Stamping Impression Simulation (Paper Imprint)", color='#1c1c1e', fontsize=14, pad=12, fontweight='bold')
    ax4.set_xticks([])
    ax4.set_yticks([])

    plt.tight_layout()
    render_file = save_path
    plt.savefig(render_file, dpi=180, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"3D Preview rendered and saved to: {render_file}")
else:
    print(f"STL not found yet at {stl_path}")
