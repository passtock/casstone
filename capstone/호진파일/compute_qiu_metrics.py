"""Qiu et al. (2022, IEEE EMBC) 4대 핵심 운동학 지표 사후 분석기 (Post-hoc Kinematics Extractor)

[논문 근거]
- Qiu, Q., et al. (2022). Evaluation of changes in kinematic measures of three dimensional
  reach to grasp movements in the early subacute period of recovery from stroke. IEEE EMBC 2022.
- 4대 핵심 평가 지표:
  1. PAp  (Peak Aperture)             : 최대 손 벌림 크기 (MGA, mm)
  2. TPAp (Time to Peak Aperture)     : 동작 시작부터 최대 벌림 도달 시간 (초, s 및 %MT)
  3. TAPV (Time After Peak Velocity)  : 손목 최고속도 이후 물체 접촉까지의 감속·미세조정 시간 (초, s)
  4. RTS  (Reach Trajectory Smoothness: 손목 3차원 도달 궤적의 평활도 (Log Dimensionless Jerk & SPARC)
  [보조 지표]
  - PV   (Peak Velocity)             : 손목 3D 최고 도달 속도 (m/s)
  - TTPV (Time to Peak Velocity)     : 최고 속도 도달 시간 (초, s)
  - RGC  (Reach-Grasp Coupling)      : 도달-파지 시간적 결합 지표 (|t_PV - t_PAp|, s)

[사용법]
  python compute_qiu_metrics.py                       # 가장 최근 세션 자동 분석
  python compute_qiu_metrics.py --session-dir <경로>  # 특정 세션 폴더 분석
  python compute_qiu_metrics.py --all                 # outputs/데이터_저장 내 모든 세션 일괄 분석
"""

import os
import sys
import glob
import csv
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


def sparc(vel: np.ndarray, times: np.ndarray, fc: float = 10.0) -> Optional[float]:
    """Spectral Arc Length (SPARC) 궤적 평활도 척도"""
    if vel is None or len(vel) < 15 or np.all(np.abs(vel) < 1e-4):
        return None
    dt = float(np.mean(np.diff(times)))
    if not np.isfinite(dt) or dt <= 0:
        return None
    mag = np.abs(np.fft.rfft(vel))
    fr = np.fft.rfftfreq(len(vel), d=dt)
    m = fr <= fc
    f_s, m_s = fr[m], mag[m]
    if len(f_s) < 3 or float(np.max(m_s)) < 1e-7:
        return None
    m_s = m_s / np.max(m_s)
    return float(-np.sum(np.sqrt((np.diff(f_s) / fc) ** 2 + np.diff(m_s) ** 2)))


def compute_ldlj(times: np.ndarray, xs: np.ndarray, ys: np.ndarray, zs: np.ndarray) -> Optional[float]:
    """Qiu et al. (2022) 원문 척도: Log Dimensionless Jerk (LDLJ)
    - 값이 클수록(0에 가까울수록) 부드러운 궤적, 음수 값이 클수록 불규칙한 저크 발생
    """
    if len(times) < 15:
        return None
    dt = float(np.mean(np.diff(times)))
    dur = float(times[-1] - times[0])
    if dur < 0.1 or dt <= 0:
        return None

    # 가속도 -> 저크 계산
    vx = np.gradient(xs, dt)
    vy = np.gradient(ys, dt)
    vz = np.gradient(zs, dt)

    ax = np.gradient(vx, dt)
    ay = np.gradient(vy, dt)
    az = np.gradient(vz, dt)

    jx = np.gradient(ax, dt)
    jy = np.gradient(ay, dt)
    jz = np.gradient(az, dt)

    jerk_sq = jx**2 + jy**2 + jz**2

    # 실제 이동 궤적 총 길이 (D)
    dr = np.sqrt(np.diff(xs)**2 + np.diff(ys)**2 + np.diff(zs)**2)
    dist = float(np.sum(dr))
    if dist < 0.01:
        return None

    # 시간 적분
    trapz_fn = getattr(np, 'trapezoid', getattr(np, 'trapz', None))
    integral = trapz_fn(jerk_sq, times)
    dimless_jerk = (dur**5 / (dist**2)) * integral
    if dimless_jerk <= 0:
        return None

    return float(-np.log(dimless_jerk))


def smooth_moving_average(arr: np.ndarray, window_size: int = 5) -> np.ndarray:
    """노이즈 제거를 위한 경량 이동 평균 필터"""
    if len(arr) < window_size:
        return arr
    window = np.ones(window_size) / window_size
    smoothed = np.convolve(arr, window, mode='same')
    smoothed[:window_size//2] = arr[:window_size//2]
    smoothed[-window_size//2:] = arr[-window_size//2:]
    return smoothed


class QiuKinematicsAnalyzer:
    """단일 세션 폴더로부터 Qiu (2022) 4대 지표를 정밀 추출하는 분석기"""

    def __init__(self, session_dir: str):
        self.session_dir = session_dir
        self.cont_csv = self._find_file("*_continuous_raw.csv")
        self.lm_csv = self._find_file("*_landmarks.csv")
        self.trials_csv = self._find_file("*_trials_summary.csv")

        if not self.cont_csv or not self.lm_csv or not self.trials_csv:
            raise FileNotFoundError(f"세션 필수 CSV 파일이 누락되었습니다: {session_dir}")

    def _find_file(self, pattern: str) -> Optional[str]:
        matches = glob.glob(os.path.join(self.session_dir, pattern))
        return matches[0] if matches else None

    def load_trials_metadata(self) -> List[Dict]:
        trials = []
        with open(self.trials_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                trials.append({
                    "trial_str": row.get("Trial", "Trial #1"),
                    "hand": row.get("Hand", "Left"),
                    "task": row.get("Task", ""),
                    "start_s": float(row.get("Start_s", 0.0)),
                    "end_s": float(row.get("End_s", 0.0)),
                    "duration_s": float(row.get("Duration_s", 0.0))
                })
        return trials

    def extract_trial_kinematics(self, trial_meta: Dict) -> Optional[Dict]:
        t_start = trial_meta["start_s"]
        t_end = trial_meta["end_s"]
        hand = trial_meta["hand"]

        # 1. Continuous CSV에서 Grip Aperture 시계열 추출
        ap_times, ap_vals_mm = [], []
        with open(self.cont_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                t = float(row['time_s'])
                if t_start <= t <= t_end and row['hand'] == hand:
                    # 3D mm 우선, 없으면 cm*10 변환
                    val = row.get('Grip_Aperture_mm_3D') or row.get('Grip_Aperture_mm_3D_cal')
                    if val and val.strip():
                        ap_times.append(t)
                        ap_vals_mm.append(float(val))
                    elif row.get('Grip_Aperture_cm_filt'):
                        ap_times.append(t)
                        ap_vals_mm.append(float(row['Grip_Aperture_cm_filt']) * 10.0)

        # 2. Landmarks CSV에서 손목(Landmark 0) 3D 좌표 시계열 추출
        wrist_times, xs, ys, zs = [], [], [], []
        with open(self.lm_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Landmark_ID') == '0' and row.get('Hand') == hand:
                    t = float(row['time_s'])
                    if t_start <= t <= t_end:
                        # 일관된 MediaPipe 3D World (m) 좌표 추출
                        if row.get('MP_X_m') and row.get('MP_Y_m') and row.get('MP_Z_m'):
                            wrist_times.append(t)
                            xs.append(float(row['MP_X_m']))
                            ys.append(float(row['MP_Y_m']))
                            zs.append(float(row['MP_Z_m']))

        if len(wrist_times) < 15 or len(ap_times) < 15:
            print(f"[경고] {trial_meta['trial_str']} 데이터 샘플 수 부족 ({len(wrist_times)} 프레임), 분석 건너뜀.")
            return None

        # 중복 타임스탬프 제거
        wrist_times = np.array(wrist_times)
        u_mask = np.diff(wrist_times, prepend=-1) > 1e-4
        wrist_times = wrist_times[u_mask]
        xs = smooth_moving_average(np.array(xs)[u_mask], window_size=5)
        ys = smooth_moving_average(np.array(ys)[u_mask], window_size=5)
        zs = smooth_moving_average(np.array(zs)[u_mask], window_size=5)

        ap_times = np.array(ap_times)
        ap_mask = np.diff(ap_times, prepend=-1) > 1e-4
        ap_times = ap_times[ap_mask]
        ap_vals_mm = smooth_moving_average(np.array(ap_vals_mm)[ap_mask], window_size=5)

        # 3. 손목 3D 접선 속도 (Tangential Velocity) 계산
        dt = np.diff(wrist_times)
        dx = np.diff(xs)
        dy = np.diff(ys)
        dz = np.diff(zs)
        vel = np.sqrt(dx**2 + dy**2 + dz**2) / np.maximum(dt, 1e-4)
        vel = smooth_moving_average(vel, window_size=5)
        t_vel = (wrist_times[:-1] + wrist_times[1:]) / 2.0

        # 최고 속도 (PV)
        pv = float(np.max(vel))
        pv_idx = int(np.argmax(vel))
        t_pv = float(t_vel[pv_idx])

        # 4. Qiu (2022) 도달 구간 분할 (Segmentation)
        # Onset: 손목 속도가 피크 속도의 5%를 초과하는 최초 시점
        thresh_5pct = 0.05 * pv
        pre_pv_indices = np.where(vel[:pv_idx] <= thresh_5pct)[0]
        if len(pre_pv_indices) > 0:
            onset_idx = pre_pv_indices[-1]
            t_onset = float(t_vel[onset_idx])
        else:
            t_onset = float(wrist_times[0])

        # Offset: 피크 이후 속도가 5% 이하로 떨어지거나 최저점에 도달한 시점
        post_pv_indices = np.where(vel[pv_idx:] <= thresh_5pct)[0]
        if len(post_pv_indices) > 0:
            offset_idx = pv_idx + post_pv_indices[0]
            t_offset = float(t_vel[offset_idx])
        else:
            t_offset = float(wrist_times[-1])

        reach_dur = max(0.01, t_offset - t_onset)

        # 5. [지표 1] PAp (Peak Aperture) & [지표 2] TPAp (Time to Peak Aperture)
        # 도달 구간 [t_onset, t_offset] 내에서의 파지폭 최댓값
        reach_ap_mask = (ap_times >= t_onset) & (ap_times <= t_offset)
        if np.any(reach_ap_mask):
            target_ap_vals = ap_vals_mm[reach_ap_mask]
            target_ap_times = ap_times[reach_ap_mask]
            pap_mm = float(np.max(target_ap_vals))
            pap_idx = int(np.argmax(target_ap_vals))
            t_pap = float(target_ap_times[pap_idx])
        else:
            pap_mm = float(np.max(ap_vals_mm))
            pap_idx = int(np.argmax(ap_vals_mm))
            t_pap = float(ap_times[pap_idx])

        tpap_s = max(0.0, t_pap - t_onset)
        tpap_pct_mt = (tpap_s / reach_dur) * 100.0

        # 6. [지표 3] TAPV (Time After Peak Velocity) & TTPV (Time to Peak Velocity)
        ttpv_s = max(0.0, t_pv - t_onset)
        tapv_s = max(0.0, t_offset - t_pv)

        # 7. [지표 4] RTS (Reach Trajectory Smoothness)
        # 도달 구간 손목 궤적으로 계산
        reach_w_mask = (wrist_times >= t_onset) & (wrist_times <= t_offset)
        if np.sum(reach_w_mask) >= 10:
            r_ts = wrist_times[reach_w_mask]
            r_xs = xs[reach_w_mask]
            r_ys = ys[reach_w_mask]
            r_zs = zs[reach_w_mask]
            r_vel = np.sqrt(np.diff(r_xs)**2 + np.diff(r_ys)**2 + np.diff(r_zs)**2) / np.maximum(np.diff(r_ts), 1e-4)
            r_vel_t = (r_ts[:-1] + r_ts[1:]) / 2.0
            rts_ldlj = compute_ldlj(r_ts, r_xs, r_ys, r_zs)
            rts_sparc = sparc(r_vel, r_vel_t)
        else:
            rts_ldlj = compute_ldlj(wrist_times, xs, ys, zs)
            rts_sparc = sparc(vel, t_vel)

        # 8. Reach-Grasp Coupling (RGC)
        rgc_s = abs(t_pv - t_pap)

        return {
            "trial": trial_meta["trial_str"],
            "hand": hand,
            "task": trial_meta["task"],
            "t_onset": t_onset,
            "t_offset": t_offset,
            "reach_dur": reach_dur,
            "pv_m_s": pv,
            "t_pv": t_pv,
            "ttpv_s": ttpv_s,
            "tapv_s": tapv_s,
            "pap_mm": pap_mm,
            "t_pap": t_pap,
            "tpap_s": tpap_s,
            "tpap_pct": tpap_pct_mt,
            "rts_ldlj": rts_ldlj,
            "rts_sparc": rts_sparc,
            "rgc_s": rgc_s,
            # 시각화용 데이터
            "plot_data": {
                "wrist_times": wrist_times,
                "t_vel": t_vel,
                "vel": vel,
                "ap_times": ap_times,
                "ap_vals_mm": ap_vals_mm,
                "xs": xs, "ys": ys, "zs": zs
            }
        }

    def generate_plot(self, results: List[Dict], save_path: str):
        """논문 보고용 고해상도 운동학 시각화 차트 생성"""
        if not results:
            return

        fig, axes = plt.subplots(len(results), 2, figsize=(14, 4.2 * len(results)), squeeze=False)
        fig.suptitle("Qiu et al. (2022) 3D Reach-to-Grasp 운동학 정밀 분석", fontsize=15, fontweight='bold')

        for i, res in enumerate(results):
            p = res["plot_data"]
            ax_v = axes[i, 0]
            ax_ap = axes[i, 1]

            # 1. 손목 속도 곡선 (PV, TAPV, Onset, Offset)
            ax_v.plot(p["t_vel"], p["vel"], color="#2563eb", lw=2, label="손목 3D 속도 (m/s)")
            ax_v.axvline(res["t_onset"], color="#10b981", ls="--", lw=1.5, label=f"도달 시작 t0 ({res['t_onset']:.2f}s)")
            ax_v.axvline(res["t_pv"], color="#ef4444", ls="-", lw=2, label=f"피크 속도 PV ({res['pv_m_s']:.2f} m/s)")
            ax_v.axvline(res["t_offset"], color="#64748b", ls="--", lw=1.5, label=f"도달 종료 ({res['t_offset']:.2f}s)")
            ax_v.axvspan(res["t_pv"], res["t_offset"], color="#ef4444", alpha=0.15, label=f"TAPV (감속시간: {res['tapv_s']:.2f}s)")

            ax_v.set_title(f"[{res['trial']} - {res['hand']}] 손목 속도 프로파일 & TAPV", fontsize=11, fontweight='bold')
            ax_v.set_xlabel("시간 (초)")
            ax_v.set_ylabel("속도 (m/s)")
            ax_v.grid(True, ls=":", alpha=0.6)
            ax_v.legend(loc="upper right", fontsize=8.5)

            # 2. 파지폭(Aperture) 곡선 (PAp, TPAp)
            ax_ap.plot(p["ap_times"], p["ap_vals_mm"], color="#8b5cf6", lw=2, label="파지 간격 (mm)")
            ax_ap.plot(res["t_pap"], res["pap_mm"], marker="o", color="#d97706", markersize=8, label=f"최대 벌림 PAp ({res['pap_mm']:.1f} mm)")
            ax_ap.axvline(res["t_onset"], color="#10b981", ls="--", lw=1.5)
            ax_ap.axvspan(res["t_onset"], res["t_pap"], color="#f59e0b", alpha=0.15, label=f"TPAp (벌림 도달시간: {res['tpap_s']:.2f}s)")

            ldlj_str = f"{res['rts_ldlj']:.2f}" if res['rts_ldlj'] is not None else "N/A"
            sparc_str = f"{res['rts_sparc']:.2f}" if res['rts_sparc'] is not None else "N/A"
            ax_ap.set_title(f"파지 간격 궤적 & 평활도 (RTS LDLJ={ldlj_str}, SPARC={sparc_str})", fontsize=11, fontweight='bold')
            ax_ap.set_xlabel("시간 (초)")
            ax_ap.set_ylabel("간격 (mm)")
            ax_ap.grid(True, ls=":", alpha=0.6)
            ax_ap.legend(loc="upper right", fontsize=8.5)

        plt.tight_layout()
        plt.subplots_adjust(top=0.92)
        fig.savefig(save_path, dpi=200)
        plt.close(fig)
        print(f"[+] 시각화 차트 저장 완료: {save_path}")

    def run(self) -> Tuple[str, str]:
        trials_meta = self.load_trials_metadata()
        print(f"[*] 세션 디렉터리: {self.session_dir}")
        print(f"[*] 총 {len(trials_meta)}개 트라이얼에 대해 Qiu (2022) 4대 지표 추출 시작...")

        results = []
        for tm in trials_meta:
            res = self.extract_trial_kinematics(tm)
            if res:
                results.append(res)

        if not results:
            print("[-] 유효한 키네마틱스 분석 결과가 없습니다.")
            return "", ""

        # CSV 저장
        csv_path = os.path.join(self.session_dir, "qiu_kinematics_summary.csv")
        headers = [
            "Trial", "Hand", "Task", "Reach_Duration_s",
            "PV_m_s", "TTPV_s", "TAPV_s",
            "PAp_mm", "TPAp_s", "TPAp_pct_MT",
            "RTS_LDLJ", "RTS_SPARC", "Reach_Grasp_Coupling_s"
        ]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in results:
                w.writerow([
                    r["trial"], r["hand"], r["task"], f"{r['reach_dur']:.3f}",
                    f"{r['pv_m_s']:.3f}", f"{r['ttpv_s']:.3f}", f"{r['tapv_s']:.3f}",
                    f"{r['pap_mm']:.2f}", f"{r['tpap_s']:.3f}", f"{r['tpap_pct']:.1f}",
                    f"{r['rts_ldlj']:.3f}" if r["rts_ldlj"] is not None else "",
                    f"{r['rts_sparc']:.3f}" if r["rts_sparc"] is not None else "",
                    f"{r['rgc_s']:.3f}"
                ])
        print(f"[+] 4대 지표 CSV 저장 완료: {csv_path}")

        # 차트 플롯 저장
        plot_path = os.path.join(self.session_dir, "qiu_kinematics_plots.png")
        self.generate_plot(results, plot_path)

        # 터미널 리포트 출력
        print("\n" + "=" * 80)
        print("          Qiu et al. (2022) 도달-파지 운동학 4대 지표 분석 결과 요약")
        print("=" * 80)
        print(f"{'Trial':<10} | {'Hand':<6} | {'PAp(mm)':<9} | {'TPAp(s)':<8} | {'TAPV(s)':<8} | {'RTS(LDLJ)':<10} | {'PV(m/s)':<8}")
        print("-" * 80)
        for r in results:
            ldlj_s = f"{r['rts_ldlj']:.2f}" if r['rts_ldlj'] is not None else "-"
            print(f"{r['trial']:<10} | {r['hand']:<6} | {r['pap_mm']:>8.1f}  | {r['tpap_s']:>7.3f}s | {r['tapv_s']:>7.3f}s | {ldlj_s:>10} | {r['pv_m_s']:>7.2f}")
        print("=" * 80 + "\n")

        return csv_path, plot_path


def main():
    parser = argparse.ArgumentParser(description="Qiu (2022) 재활 운동학 4대 지표 사후 분석기")
    parser.add_argument("--session-dir", type=str, default=None, help="분석할 세션 폴더 경로 (미지정 시 최신 세션 자동 선택)")
    parser.add_argument("--all", action="store_true", help="모든 세션 일괄 분석")
    args = parser.parse_args()

    data_root = "C:/Users/passp/OneDrive/바탕 화면/jeayong/capstone/호진파일/outputs/데이터_저장"

    if args.all:
        sessions = [os.path.join(data_root, d) for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))]
        print(f"[*] 총 {len(sessions)}개 세션 일괄 분석을 시작합니다.")
        for s in sorted(sessions):
            try:
                analyzer = QiuKinematicsAnalyzer(s)
                analyzer.run()
            except Exception as e:
                print(f"[-] {s} 분석 중 오류 발생: {e}")
        return

    if args.session_dir:
        target_dir = args.session_dir
    else:
        # 가장 최근 세션 디렉터리 자동 탐색
        sessions = [os.path.join(data_root, d) for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d))]
        if not sessions:
            print(f"[오류] 데이터 저장 폴더에 세션이 없습니다: {data_root}")
            return
        target_dir = max(sessions, key=os.path.getmtime)
        print(f"[*] 최신 세션 자동 감지: {target_dir}")

    analyzer = QiuKinematicsAnalyzer(target_dir)
    analyzer.run()


if __name__ == "__main__":
    main()
