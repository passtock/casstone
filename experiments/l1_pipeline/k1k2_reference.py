# -*- coding: utf-8 -*-
"""
L1 추적 파이프라인 참조 구현 (v6 계획 §0-4 D14)
================================================

목적
----
1) D14 명세(10단계)를 실행 가능한 코드로 고정한다.
2) 오라클 테스트 T1~T6으로 명세가 의도대로 동작하는지 검증한다.
3) 실제 RGB-D 데이터가 들어오기 전에 **실패 모드를 미리 확인**한다.

⚠️ 중요: 이 파일은 **합성 깊이 영상**만 만든다. 우리 카메라 데이터가 아니다.
   실제 성능은 §7 계측 검증에서 측정해야 한다.

D14 명세 요약
-------------
1. depth를 color에 정렬 (실데이터에서 SDK가 수행; 여기서는 좌표가 이미 정렬됐다고 가정)
2. MediaPipe Hands 21점: WRIST=0, THUMB_TIP=4, INDEX_FINGER_TIP=8
3. 표면점 = 랜드마크 픽셀 중심 5x5 창 depth 중앙값 (유효비율 >= 50% 필요)
4. 정렬된 intrinsics로 3D 역투영
5. 손-일관성 검사 (아래 '수정' 참조)
6. K1 = (THUMB_TIP, INDEX_FINGER_TIP) 거리의 P95, 양쪽 유효 프레임만
7. K2 = WRIST 3D 속도의 P95, 연속 유효 쌍만, dt <= 0.1 s
8. 필터 없음 (주 후보값)
9. 장치 타임스탬프로 dt
10. 검출 실패 = 하드 결측, 보간 금지

수정 사항 (D14 5단계)
---------------------
초기 명세는 "표면점 depth가 손목 depth ± 120 mm 밖이면 무효"였으나
**3D 거리(손목-손끝) ∈ [60, 230] mm** 로 교체했다.
이유: 손이 카메라 쪽을 향하면 손끝이 손목보다 100 mm 이상 앞에 정상적으로 온다.
      depth만 비교하면 **정상 자세를 오탐**한다. 3D 거리는 자세에 불변이다.

알려진 한계 (반드시 보고할 것)
------------------------------
접촉 순간에는 손가락 패드와 물체 표면의 depth가 거의 같아서,
랜드마크가 물체 위에 찍혀도 **depth·기하 검사로는 구분할 수 없다.**
→ 이 오류는 **가림 주석**과 **시행 수준 패턴**으로만 잡힌다.
→ 따라서 검사별 검출률을 가림 주석 대비로 **결과로 보고**해야 한다.

실행:
  python experiments/l1_pipeline/k1k2_reference.py --selftest
"""

import io
import math
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- MediaPipe Hands 공식 인덱스 -------------------------------------------
WRIST = 0
THUMB_TIP = 4
INDEX_FINGER_TIP = 8

# --- D14 파라미터 ---------------------------------------------------------
WINDOW_K = 5                 # 5x5 창
MIN_VALID_FRAC = 0.5         # 창 내 유효 depth 비율 하한
MAX_GAP_S = 0.1              # 이보다 긴 결측은 가로질러 속도를 계산하지 않음
HAND_DIST_LO_MM = 60.0       # 손목-손끝 3D 거리 하한
HAND_DIST_HI_MM = 230.0      # 상한


# ===========================================================================
# 1. 기본 자료구조
# ===========================================================================
class Intrinsics:
    def __init__(self, fx, fy, cx, cy):
        self.fx, self.fy, self.cx, self.cy = fx, fy, cx, cy


class Frame:
    """depth_mm: 평탄 리스트, 0 = 무효. (u,v)는 픽셀 좌표."""

    def __init__(self, width, height, depth_mm):
        self.width = width
        self.height = height
        self.d = depth_mm

    def at(self, u, v):
        if u < 0 or v < 0 or u >= self.width or v >= self.height:
            return 0
        return self.d[v * self.width + u]


def median_window(frame, u, v, k=WINDOW_K, min_frac=MIN_VALID_FRAC):
    """랜드마크 픽셀 중심 k x k 창의 depth 중앙값. 유효비율 미달이면 (None, frac)."""
    half = k // 2
    vals = []
    total = k * k
    for dv in range(-half, half + 1):
        for du in range(-half, half + 1):
            z = frame.at(u + du, v + dv)
            if z > 0:
                vals.append(z)
    frac = len(vals) / float(total)
    if frac < min_frac or not vals:
        return None, frac
    return statistics.median(vals), frac


def backproject(u, v, d_mm, intr):
    """정렬된 intrinsics로 역투영. 반환 단위 mm."""
    x = (u - intr.cx) * d_mm / intr.fx
    y = (v - intr.cy) * d_mm / intr.fy
    return (x, y, d_mm)


def dist3(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def p95(xs):
    if not xs:
        return None
    s = sorted(xs)
    k = 0.95 * (len(s) - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# ===========================================================================
# 2. 표면점 (D14 3~5단계)
# ===========================================================================
def surface_point(frame, uv, intr):
    """(point3d | None, reason). reason: ok / no_landmark / no_valid_depth"""
    if uv is None:
        return None, "no_landmark"
    d, frac = median_window(frame, uv[0], uv[1])
    if d is None:
        return None, "no_valid_depth(%.2f)" % frac
    return backproject(uv[0], uv[1], d, intr), "ok"


def hand_consistency(wrist_pt, tip_pt,
                     lo=HAND_DIST_LO_MM, hi=HAND_DIST_HI_MM):
    """3D 거리 기반. 자세 불변. (bool, dist)"""
    if wrist_pt is None or tip_pt is None:
        return False, None
    dd = dist3(wrist_pt, tip_pt)
    return (lo <= dd <= hi), dd


# ===========================================================================
# 3. 트랙 구성 (프레임별 유효점)
# ===========================================================================
def build_track(frames, landmarks_per_frame, intr, consistency=True):
    """
    frames: Frame 리스트
    landmarks_per_frame: [{WRIST:(u,v)|None, THUMB_TIP:..., INDEX_FINGER_TIP:...}, ...]
    반환: [{"t":i, "wrist":pt|None, "thumb":pt|None, "index":pt|None, "reasons":{...}}, ...]
    """
    track = []
    for i, (fr, lm) in enumerate(zip(frames, landmarks_per_frame)):
        rec = {"t": i, "reasons": {}, "dist_check": {}}
        pts = {}
        for name in (WRIST, THUMB_TIP, INDEX_FINGER_TIP):
            pt, why = surface_point(fr, lm.get(name), intr)
            pts[name] = pt
            rec["reasons"][name] = why
        if consistency:
            for name in (THUMB_TIP, INDEX_FINGER_TIP):
                ok, dd = hand_consistency(pts[WRIST], pts[name])
                rec["dist_check"][name] = (ok, dd)
                if not ok:
                    pts[name] = None
                    rec["reasons"][name] = "hand_consistency_fail(%s)" % (
                        "%.0fmm" % dd if dd is not None else "n/a")
        rec["wrist"] = pts[WRIST]
        rec["thumb"] = pts[THUMB_TIP]
        rec["index"] = pts[INDEX_FINGER_TIP]
        track.append(rec)
    return track


# ===========================================================================
# 4. K1 / K2 (D14 6~7단계)
# ===========================================================================
def compute_k1(track, fps=30.0):
    ds = []
    for rec in track:
        if rec["thumb"] is not None and rec["index"] is not None:
            ds.append(dist3(rec["thumb"], rec["index"]))
    return p95(ds), len(ds)


def compute_k2(track, fps=30.0, max_gap_s=MAX_GAP_S):
    """연속 유효 쌍만. 결측을 가로지르지 않는다."""
    speeds = []
    spans = []          # (i_from, i_to) 실제로 계산한 쌍 (테스트용)
    prev = None
    for rec in track:
        cur = rec["wrist"]
        if cur is None:
            prev = None          # 하드 결측 -> 연결 끊기
            continue
        if prev is not None:
            i0, p0 = prev
            dt = (rec["t"] - i0) / fps
            if 0 < dt <= max_gap_s:
                speeds.append(dist3(cur, p0) / dt)
                spans.append((i0, rec["t"]))
            # dt가 크면 계산하지 않음 (결측 가로지르기 금지)
        prev = (rec["t"], cur)
    return p95(speeds), len(speeds), spans


# ===========================================================================
# 5. 합성 씬
# ===========================================================================
BG_DEPTH = 2400   # 배경 (mm)


def blank_frame(w, h, bg=BG_DEPTH):
    return Frame(w, h, [bg] * (w * h))


def paint_disc(frame, u0, v0, r, depth_mm):
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            if du * du + dv * dv <= r * r:
                u, v = u0 + du, v0 + dv
                if 0 <= u < frame.width and 0 <= v < frame.height:
                    frame.d[v * frame.width + u] = depth_mm


def punch_hole(frame, u0, v0, r):
    """유효 depth를 0으로 만든다 (depth 구멍 흉내)."""
    for dv in range(-r, r + 1):
        for du in range(-r, r + 1):
            if du * du + dv * dv <= r * r:
                u, v = u0 + du, v0 + dv
                if 0 <= u < frame.width and 0 <= v < frame.height:
                    frame.d[v * frame.width + u] = 0


# ===========================================================================
# 6. 오라클 테스트
# ===========================================================================
RESULTS = []


def log(s=""):
    print(s)
    RESULTS.append(s)


def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    log("  %-46s %s  %s" % (name, tag, detail))
    return bool(cond)


def make_scene(n_frames, wrist_uv, thumb_uv, index_uv,
               z_wrist=750.0, z_thumb=None, z_index=None,
               thumb_disc_r=4, index_disc_r=4, wrist_disc_r=6,
               thumb_path=None, wrist_path=None):
    """프레임별 합성 씬 + 랜드마크 생성."""
    w, h = 640, 480
    intr = Intrinsics(fx=500.0, fy=500.0, cx=320.0, cy=240.0)
    if z_thumb is None:
        z_thumb = z_wrist
    if z_index is None:
        z_index = z_wrist

    frames, lms = [], []
    for i in range(n_frames):
        fr = blank_frame(w, h)
        wu = wrist_path(i) if wrist_path else wrist_uv
        tu = thumb_path(i) if thumb_path else thumb_uv
        iu = index_uv
        zw = wrist_path.depth(i) if hasattr(wrist_path, "depth") else z_wrist

        paint_disc(fr, wu[0], wu[1], wrist_disc_r, zw)
        paint_disc(fr, tu[0], tu[1], thumb_disc_r, z_thumb)
        paint_disc(fr, iu[0], iu[1], index_disc_r, z_index)
        frames.append(fr)
        lms.append({WRIST: wu, THUMB_TIP: tu, INDEX_FINGER_TIP: iu})
    return intr, frames, lms


def selftest():
    log("=== L1 파이프라인 오라클 (D14 명세 검증) ===")
    log("")
    intr = Intrinsics(fx=500.0, fy=500.0, cx=320.0, cy=240.0)
    ok_all = True

    # ---------------------------------------------------------------------
    # T1: K1 정확값.  Z=750, 픽셀 차이로 거리 결정.
    #     wrist(320,240), thumb(320,200) -> 40 px = 750*40/500 = 60.0 mm
    #     index(320,190)                -> thumb-index 10 px = 15.0 mm
    # ---------------------------------------------------------------------
    log("[T1] K1 정확값 (정지, 20프레임)")
    _, frames, lms = make_scene(20, (320, 240), (320, 200), (320, 190))
    track = build_track(frames, lms, intr)
    k1, n1 = compute_k1(track)
    ok_all &= check("K1 == 15.0 mm", abs(k1 - 15.0) < 1e-9, "got %.6f (n=%d)" % (k1, n1))
    ok_all &= check("유효 프레임 20개", n1 == 20, "n=%d" % n1)

    # ---------------------------------------------------------------------
    # T1b: K2 정확값. 손목이 프레임당 PX px 이동 at 30 fps
    #      속도 = px * (Z / fy) * fps  [mm/s]   <- 산술을 코드로 계산해 실수 방지
    # ---------------------------------------------------------------------
    PX = 10.0
    Z = 750.0
    FPS = 30.0
    expected_speed = PX * (Z / intr.fy) * FPS     # 10 px * 1.5 mm/px * 30 = 450 mm/s
    log("[T1b] K2 정확값 (%.0f px/프레임 @ %.0f mm, fy=%.0f -> %.1f mm/s)"
        % (PX, Z, intr.fy, expected_speed))

    class WPath:
        def __call__(self, i):
            return (320, int(240 + PX * i))

        def depth(self, i):
            return Z

    _, frames, lms = make_scene(11, None, (320, 220), (320, 215), wrist_path=WPath())
    track = build_track(frames, lms, intr)
    k2, n2, spans = compute_k2(track)
    ok_all &= check("K2 == %.1f mm/s" % expected_speed,
                    abs(k2 - expected_speed) < 1e-6, "got %.4f (n=%d)" % (k2, n2))
    ok_all &= check("속도 쌍 10개(연속 11프레임)", len(spans) == 10, "n=%d" % len(spans))

    # ---------------------------------------------------------------------
    # T2: 가려진 랜드마크 -> 검사가 잡아내는가 + 검사 없으면 얼마나 틀리는가
    # ---------------------------------------------------------------------
    log("[T2] 가려진 랜드마크(배경으로 +1650 mm 이동) 탐지")
    w, h = 640, 480
    frames, lms = [], []
    for i in range(20):
        fr = blank_frame(w, h)
        paint_disc(fr, 320, 240, 6, 750)      # wrist
        paint_disc(fr, 320, 190, 4, 750)      # index
        if 8 <= i <= 12:
            # thumb 랜드마크는 손을 벗어나 배경 위에 찍힘 (MediaPipe 이슈 #3008)
            tu = (320, 200)
            paint_disc(fr, 320, 200, 4, 2400)
        else:
            tu = (320, 200)
            paint_disc(fr, 320, 200, 4, 750)
        frames.append(fr)
        lms.append({WRIST: (320, 240), THUMB_TIP: tu, INDEX_FINGER_TIP: (320, 190)})

    tr_on = build_track(frames, lms, intr, consistency=True)
    tr_off = build_track(frames, lms, intr, consistency=False)
    k1_on, n_on = compute_k1(tr_on)
    k1_off, n_off = compute_k1(tr_off)
    bad_frames = [i for i, r in enumerate(tr_on)
                  if r["reasons"][THUMB_TIP].startswith("hand_consistency_fail")]
    ok_all &= check("가림 5프레임 전부 검출", bad_frames == [8, 9, 10, 11, 12], str(bad_frames))
    ok_all &= check("검사 ON: K1 = 15.0 mm 유지", abs(k1_on - 15.0) < 1e-9,
                    "got %.4f (n=%d)" % (k1_on, n_on))
    ok_all &= check("검사 OFF: K1이 오염됨(>100 mm)", k1_off > 100,
                    "got %.1f mm (n=%d)  <- 검사가 없으면 이만큼 틀린다" % (k1_off, n_off))

    # ---------------------------------------------------------------------
    # T3: 창 내 유효 depth 부족 -> 무효
    # ---------------------------------------------------------------------
    log("[T3] 창 내 유효 depth 40% -> 그 점 무효")
    fr = blank_frame(w, h)
    paint_disc(fr, 320, 240, 6, 750)
    paint_disc(fr, 320, 190, 4, 750)
    paint_disc(fr, 320, 200, 4, 750)
    punch_hole(fr, 320, 200, 2)   # 5x5 창에서 13/25 = 52% 무효 -> 48% 유효
    pt, why = surface_point(fr, (320, 200), intr)
    ok_all &= check("유효비율 미달로 무효 처리", pt is None and why.startswith("no_valid_depth"),
                    why)

    # ---------------------------------------------------------------------
    # T4: 0.33초 결측 -> 결측을 가로지르는 속도를 계산하지 않는다
    # ---------------------------------------------------------------------
    PX4 = 5.0
    expected4 = PX4 * (750.0 / intr.fy) * 30.0      # 5 px * 1.5 mm * 30 = 225 mm/s
    log("[T4] 0.33초(10프레임) 결측 구간을 가로지르는 속도 금지 (기대 %.1f mm/s)" % expected4)
    frames, lms = [], []
    for i in range(30):
        fr = blank_frame(w, h)
        u = int(320 + PX4 * i)          # u 방향으로 이동(프레임 폭 640 안)
        if 10 <= i < 20:
            frames.append(fr)
            lms.append({WRIST: None, THUMB_TIP: None, INDEX_FINGER_TIP: None})
            continue
        paint_disc(fr, u, 240, 6, 750)
        paint_disc(fr, u, 220, 4, 750)
        paint_disc(fr, u, 215, 4, 750)
        frames.append(fr)
        lms.append({WRIST: (u, 240), THUMB_TIP: (u, 220), INDEX_FINGER_TIP: (u, 215)})
    track = build_track(frames, lms, intr)
    k2, n2, spans = compute_k2(track)
    crossing = [(a, b) for a, b in spans if a < 10 and b >= 20]
    ok_all &= check("결측 가로지르는 쌍 0개", len(crossing) == 0, str(crossing))
    ok_all &= check("계산된 속도 전부 %.1f mm/s" % expected4,
                    abs(k2 - expected4) < 1e-6, "got %.4f" % k2)

    # ---------------------------------------------------------------------
    # T5: 랜드마크가 아예 없으면 하드 결측 (보간 없음)
    # ---------------------------------------------------------------------
    log("[T5] 전 구간 랜드마크 없음 -> 값 없음(보간 금지)")
    frames = [blank_frame(w, h) for _ in range(5)]
    lms = [{WRIST: None, THUMB_TIP: None, INDEX_FINGER_TIP: None}] * 5
    track = build_track(frames, lms, intr)
    k1, n1 = compute_k1(track)
    k2, n2, spans = compute_k2(track)
    ok_all &= check("K1/K2 = None", k1 is None and k2 is None, "k1=%s n1=%d" % (k1, n1))

    # ---------------------------------------------------------------------
    # T6: 손이 카메라를 향하는 정상 자세를 오탐하지 않는가 (depth 비교 폐기 근거)
    # ---------------------------------------------------------------------
    log("[T6] 정상 자세(손끝이 손목보다 100 mm 앞) 오탐 없음")
    fr = blank_frame(w, h)
    paint_disc(fr, 320, 240, 6, 750)     # wrist
    paint_disc(fr, 320, 200, 4, 650)     # thumb: 40 px 위 + 100 mm 앞
    paint_disc(fr, 320, 190, 4, 650)     # index
    lm = {WRIST: (320, 240), THUMB_TIP: (320, 200), INDEX_FINGER_TIP: (320, 190)}
    track = build_track([fr], [lm], intr, consistency=True)
    reason = track[0]["reasons"][THUMB_TIP]
    dd = track[0]["dist_check"][THUMB_TIP][1]
    ok_all &= check("오탐 없음(3D 거리 기준 통과)", reason == "ok",
                    "3D 거리=%.1f mm (depth 차이는 100 mm)" % dd)

    log("")
    log("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    log("")
    log("※ 합성 데이터다. 실제 성능은 §7 계측 검증에서 측정한다.")
    return ok_all


def main():
    if "--selftest" in sys.argv:
        ok = selftest()
        experiments_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = os.path.join(experiments_dir, "results", "l1_pipeline_oracle.txt")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with io.open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(RESULTS) + "\n")
        print("\n[saved] %s" % out)
        sys.exit(0 if ok else 1)
    print(__doc__)


if __name__ == "__main__":
    main()
