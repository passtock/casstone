"""trial별 환측 손 각도 궤적을 한 장에 그려 녹화 타이밍 이상 trial을 확인한다.

startPos = (처음 3프레임 평균 - 최소) / (최대 - 최소). 0이면 쥔 상태에서 시작, 1이면 이미 편 상태에서 시작.
"""
import glob
import json
import os

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 7})

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "outputs", "데이터_저장")
OUT = os.path.join(BASE, "outputs", "논문_figures")
FINGER_JOINTS = [f"{f}_{j}" for f in ("Index", "Middle", "Ring", "Pinky") for j in ("MCP", "PIP", "DIP")]
START_THRESH = 0.4

dirs = sorted(d for d in glob.glob(os.path.join(DATA, "*")) if os.path.isdir(d))
rows = []
fig, axes = plt.subplots(len(dirs), 10, figsize=(16, 1.6 * len(dirs)), squeeze=False)
for r, d in enumerate(dirs):
    meta = json.load(open(glob.glob(os.path.join(d, "*metadata.json"))[0], encoding="utf-8"))
    name = meta["subject"]["name"]
    aff = "Left" if "좌" in meta["subject"]["affected_side"] else "Right"
    raw = pd.read_csv(glob.glob(os.path.join(d, "*continuous_raw.csv"))[0], encoding="utf-8-sig")
    s = raw[(raw.hand == aff) & (raw.Trial != "Rest")]
    for c, (tr, g) in enumerate(s.groupby("Trial", sort=False)):
        a = g[[j + "_filt" for j in FINGER_JOINTS]].mean(axis=1).values
        t = g.time_s.values - g.time_s.values[0]
        k = 3
        rng = a.max() - a.min()
        start_pos = (a[:k].mean() - a.min()) / rng if rng > 0 else 0
        flags = []
        if start_pos >= START_THRESH:
            flags.append("시작 시 이미 펴짐")
        if t[-1] < 2.0:
            flags.append("너무 짧음")
        rows.append(dict(세션=name, trial=tr, 길이_s=round(t[-1], 2), 범위_deg=round(rng, 1),
                         startPos=round(start_pos, 2), 의심=", ".join(flags)))
        ax = axes[r, c]
        ax.plot(t, a, color="#d03b3b" if flags else "#2a78d6", lw=1.2)
        ax.set_title(f"{tr}  s={start_pos:.2f}", fontsize=7, color="#d03b3b" if flags else "#0b0b0b")
        ax.tick_params(labelsize=6)
    axes[r, 0].set_ylabel(name, fontsize=8)
    for c in range(len(s.Trial.unique()), 10):
        axes[r, c].axis("off")
fig.suptitle("환측 손가락(검지~소지) 평균 관절각 궤적 — 빨강: 의심 trial (y: 각도°, x: 초)", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "trial_점검.png"), dpi=130)
R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, "trial_점검.csv"), index=False, encoding="utf-8-sig")
print(R[R.의심 != ""].to_string(index=False))
