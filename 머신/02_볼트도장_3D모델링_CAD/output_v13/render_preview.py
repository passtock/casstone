import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

output_dir = os.path.dirname(os.path.abspath(__file__))

def load_stl_binary(filepath):
    with open(filepath, 'rb') as f:
        f.read(80)
        num_triangles = int.from_bytes(f.read(4), byteorder='little')
        dt = np.dtype([
            ('normal', '<f4', (3,)),
            ('v1', '<f4', (3,)),
            ('v2', '<f4', (3,)),
            ('v3', '<f4', (3,)),
            ('attr', '<u2')
        ])
        data = np.fromfile(f, dtype=dt, count=num_triangles)
        return np.stack([data['v1'], data['v2'], data['v3']], axis=1)

def render_model(d):
    stl_path = os.path.join(output_dir, f"Bolt_Stamp_D{d}mm_v13.stl")
    save_path = os.path.join(output_dir, f"Bolt_Stamp_3D_Preview_D{d}mm_v13.png")
    if not os.path.exists(stl_path):
        print(f"STL not found: {stl_path}")
        return
    print(f"Rendering D{d}mm from {stl_path}...")
    verts = load_stl_binary(stl_path)
    total_tri = len(verts)
    max_tri = 18000
    sub_verts = verts[::max(1, total_tri // max_tri)] if total_tri > max_tri else verts

    fig = plt.figure(figsize=(16, 16), facecolor="#14171c")

    # 1. Isometric View
    ax1 = fig.add_subplot(2, 2, 1, projection='3d', facecolor="#14171c")
    mesh1 = Poly3DCollection(sub_verts, alpha=0.92, edgecolor='#2c323d', linewidth=0.1)
    mesh1.set_facecolor('#8fa0b5')
    ax1.add_collection3d(mesh1)
    ax1.set_title(f"Bolt Stamp D{d}mm - Isometric View (Shaft +0.5cm & Top Loop)", color='white', fontsize=13, pad=12, fontweight='bold')
    ax1.view_init(elev=22, azim=45)

    # 2. Side View (Nameplate)
    ax2 = fig.add_subplot(2, 2, 2, projection='3d', facecolor="#14171c")
    mesh2 = Poly3DCollection(sub_verts, alpha=0.92, edgecolor='#2c323d', linewidth=0.1)
    mesh2.set_facecolor('#a4b3c6')
    ax2.add_collection3d(mesh2)
    ax2.set_title(f"Side View: Nameplate & Extended Margin (7.5mm)", color='white', fontsize=13, pad=12, fontweight='bold')
    ax2.view_init(elev=5, azim=90)

    # 3. Top View: Eyelet Loop
    ax3 = fig.add_subplot(2, 2, 3, projection='3d', facecolor="#14171c")
    mesh3 = Poly3DCollection(sub_verts, alpha=0.92, edgecolor='#2c323d', linewidth=0.1)
    mesh3.set_facecolor('#7b8c9f')
    ax3.add_collection3d(mesh3)
    ax3.set_title(f"Top-Down Angled View: Loop Through-Hole (Ø5mm)", color='white', fontsize=13, pad=12, fontweight='bold')
    ax3.view_init(elev=55, azim=60)

    # 4. Bottom View: Stamp Logo Face
    ax4 = fig.add_subplot(2, 2, 4, projection='3d', facecolor="#14171c")
    mesh4 = Poly3DCollection(sub_verts, alpha=0.92, edgecolor='#2c323d', linewidth=0.1)
    mesh4.set_facecolor('#b0c4de')
    ax4.add_collection3d(mesh4)
    ax4.set_title(f"Bottom View: Embossed Stamp Logo (Mirrored for Stamping)", color='white', fontsize=13, pad=12, fontweight='bold')
    ax4.view_init(elev=-80, azim=90)

    limit = max(d/2 + 2, 32.0)
    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_zlim(0, 65)
        ax.axis('off')

    plt.subplots_adjust(left=0.02, right=0.98, top=0.95, bottom=0.02, wspace=0.04, hspace=0.08)
    plt.savefig(save_path, dpi=160, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"Saved: {save_path} ({os.path.getsize(save_path):,} bytes)")

if __name__ == '__main__':
    for d in [30, 40]:
        render_model(d)
