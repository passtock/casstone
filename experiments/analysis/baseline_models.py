#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A0 · A0-time 대조군 — 계획서 §6 표의 **비(非)VLM** 비교 모델

계획서 §6:
    A0      | 로지스틱 회귀: K1·K2(**장애인 내 또는 과제 내 정규화**)·Q 요약·T·과제 ID
    A0-time | T·과제 ID만

왜 별도 파일인가
----------------
A0·A0-time 은 **VLM 출력이 아니다**. 따라서 `make_conditions_v6.py`(VLM 조건 생성기)가
만들지 않는다. 대신 이 모듈이 **같은 `predictions.csv` 스키마**로 예측을 내보내
`analysis_harness.py` 가 조건과 동일하게 MAE·CI·Holm 을 계산할 수 있게 한다.

구현 주의
---------
`scikit-learn` 이 설치되어 있지 않으므로 **softmax 다항 로지스틱 회귀를 numpy 로 직접 구현**했다
(경사하강 + L2). 외부 ML 의존성 0개 → 재현성 확보.

사용
----
    python experiments/analysis/baseline_models.py --selftest
    python experiments/analysis/baseline_models.py --l2 <세션폴더> --reference reference.csv \\
        --out predictions_A0.csv
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import os
import sys

import numpy as np

N_CLASSES = 4          # ARAT 항목 0/1/2/3
Q_KEYS = ["q1_pair_valid_ratio", "q2_max_gap_s", "q4_edge_mixing_frac",
          "q5_not_assessable_frac", "q3_valid_samples_k1", "q3_valid_samples_k2"]


# ===========================================================================
# 특성
# ===========================================================================
def load_l2(session_dir: str):
    out = []
    for p in sorted(glob.glob(os.path.join(session_dir, "L2_metric", "*.json"))):
        with io.open(p, "r", encoding="utf-8") as f:
            r = json.load(f)
        r.setdefault("trial_id", os.path.basename(p)[:-5])
        r["_session"] = os.path.basename(os.path.abspath(session_dir.rstrip("/\\")))
        out.append(r)
    return out


def participant(rec):
    """참여자 식별자.

    세션 폴더명이 곧 참여자다(폴더 1개 = 참여자 1명) — `20260915_비장애인_test_26세_남`.
    ⚠️ 과거 구현은 `split('_')[1]` 로 **집단명('비장애인')을 돌려줬다** → 전원이 같은 참여자로 취급되어
       장애인 단위 2-fold CV가 붕괴했다. 폴더명 전체를 쓴다.
    """
    return rec.get("_session", "")


def task_of(rec):
    tid = rec.get("trial_id", "")
    for s in tid.split("_"):
        if s.upper() in ("T1", "T2"):
            return s.upper()
    return "T1"


def patient_within_norm(values):
    """장애인 내 정규화 (§6 A0). 시행 1개뿐이면 0 을 돌려준다(정의상 중심화만 가능).

    ⚠️ '시행 내 정규화'는 정의 불가다 — K1·K2는 이미 시행당 스칼라 1개다.
       (v6.2 정정: 계획서 §6 참조)
    """
    v = np.asarray([0.0 if x is None else float(x) for x in values], dtype=float)
    m = float(np.mean(v))
    s = float(np.std(v))
    if s <= 0:
        return np.zeros_like(v)
    return (v - m) / s


def build_features(recs, use_numbers=True, use_q=True, use_time=True):
    """특성 행렬 X 와 행 메타를 만든다. A0 / A0-time 모두 이 함수로 만든다."""
    groups = {}
    for r in recs:
        groups.setdefault((participant(r), task_of(r)), []).append(r)

    norm = {}                       # (session, trial_id) -> (nk1, nk2)
    if use_numbers:
        for key, rs in groups.items():
            k1 = patient_within_norm([x.get("k1_raw_mm") for x in rs])
            k2 = patient_within_norm([x.get("k2_raw_mm") for x in rs])
            for i, x in enumerate(rs):
                norm[(x["_session"], x["trial_id"])] = (k1[i], k2[i])

    rows, meta = [], []
    for r in recs:
        f = []
        if use_numbers:
            a, b = norm.get((r["_session"], r["trial_id"]), (0.0, 0.0))
            f += [a, b]
        if use_q:
            for k in Q_KEYS:
                f.append(float(r.get("q", {}).get(k, 0.0) or 0.0))
        if use_time:
            f.append(float(r.get("observation_window_s") or 0.0))
            f.append(1.0 if task_of(r) == "T2" else 0.0)   # 과제 ID
        rows.append(f)
        meta.append({"session": r["_session"], "trial_id": r["trial_id"],
                     "participant": participant(r), "task": task_of(r)})
    return np.asarray(rows, dtype=float), meta


# ===========================================================================
# softmax 다항 로지스틱 회귀 (numpy)
# ===========================================================================
class SoftmaxLR:
    def __init__(self, n_features, n_classes=N_CLASSES, l2=1e-2, lr=0.5,
                 epochs=800, seed=20260922):
        rng = np.random.RandomState(seed)
        self.W = rng.normal(0, 0.01, size=(n_features, n_classes))
        self.b = np.zeros(n_classes)
        self.l2, self.lr, self.epochs = l2, lr, epochs

    def _softmax(self, z):
        z = z - np.max(z, axis=1, keepdims=True)
        e = np.exp(z)
        return e / np.sum(e, axis=1, keepdims=True)

    def fit(self, X, y, sample_weight=None):
        n = X.shape[0]
        sw = np.ones(n) if sample_weight is None else np.asarray(sample_weight, float)
        sw = sw / sw.sum() * n
        for _ in range(self.epochs):
            P = self._softmax(X @ self.W + self.b)
            Y = np.zeros_like(P)
            Y[np.arange(n), y] = 1.0
            G = (P - Y) * sw[:, None]
            gW = X.T @ G / n + self.l2 * self.W
            gb = G.sum(axis=0) / n
            self.W -= self.lr * gW
            self.b -= self.lr * gb
        return self

    def predict(self, X):
        return np.argmax(self._softmax(X @ self.W + self.b), axis=1)


def standardize(Xtr, Xte):
    m = Xtr.mean(axis=0)
    s = Xtr.std(axis=0)
    s[s < 1e-9] = 1.0
    return (Xtr - m) / s, (Xte - m) / s


# ===========================================================================
# 참조 점수
# ===========================================================================
def load_reference(path):
    """CSV: session, trial_id, score (필요 최소)."""
    ref = {}
    with io.open(path, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key = (r.get("session", ""), r.get("trial_id", ""))
            if r.get("score") not in (None, ""):
                ref[key] = int(float(r["score"]))
    return ref


def run(recs, ref, model_name, use_numbers, use_q, use_time, folds=2):
    """장애인 단위 2-fold 교차검증으로 out-of-fold 예측을 만든다 (§3 결정 14 준수)."""
    X, meta = build_features(recs, use_numbers, use_q, use_time)
    y = np.array([ref.get((m["session"], m["trial_id"]), -1) for m in meta])
    keep = y >= 0
    X, meta, y = X[keep], [m for m, k in zip(meta, keep) if k], y[keep]
    if len(y) == 0:
        return [], "참조 점수와 매칭되는 시행이 0건"

    pids = sorted({m["participant"] for m in meta})
    pred = np.full(len(y), -1)
    rng = np.random.RandomState(20260922)
    for fold in range(folds):
        test_pids = {p for i, p in enumerate(pids) if i % folds == fold}
        te = np.array([m["participant"] in test_pids for m in meta])
        tr = ~te
        if tr.sum() < N_CLASSES or te.sum() == 0:
            continue
        Xtr, Xte = standardize(X[tr], X[te])
        mdl = SoftmaxLR(Xtr.shape[1]).fit(Xtr, y[tr])
        pred[te] = mdl.predict(Xte)

    out = []
    for i, m in enumerate(meta):
        if pred[i] < 0:
            continue
        out.append({"condition": model_name, "injection": "none", "run": 1,
                    "session": m["session"], "trial_id": m["trial_id"],
                    "participant": m["participant"], "task": m["task"],
                    "score": int(pred[i]), "status": "ok",
                    "reference": "therapist"})
    mae = float(np.mean(np.abs(pred[pred >= 0] - y[pred >= 0]))) if (pred >= 0).any() else float("nan")
    return out, mae


PRED_FIELDS = ["condition", "injection", "run", "session", "trial_id",
               "participant", "task", "score", "status", "reference"]


def write_predictions(rows, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PRED_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ===========================================================================
# 오라클
# ===========================================================================
def selftest():
    ok_all = True
    log = []

    def chk(name, cond, detail=""):
        nonlocal ok_all
        print("  %-58s %s  %s" % (name, "PASS" if cond else "FAIL", detail))
        log.append("%s %s %s" % (name, "PASS" if cond else "FAIL", detail))
        ok_all = ok_all and bool(cond)

    def rec(sess, tid, k1, k2, T=3.5):
        return {"trial_id": tid, "_session": sess, "k1_raw_mm": k1, "k2_raw_mm": k2,
                "observation_window_s": T, "q": {k: 0.9 for k in Q_KEYS}}

    print("[A0-1] 특성 구성")
    recs = [rec("P1_세션", "P1_T1_t1", 10, 100), rec("P1_세션", "P1_T1_t2", 12, 120)]
    X, meta = build_features(recs, True, True, True)
    chk("A0 특성 수 = 2(K) + 6(Q) + 2(T,과제)", X.shape[1] == 10, str(X.shape))
    Xt, _ = build_features(recs, False, False, True)
    chk("A0-time 특성 수 = 2(T,과제)", Xt.shape[1] == 2, str(Xt.shape))
    chk("A0-time 은 K1·K2·Q 를 안 씀", Xt.shape[1] == 2 and not np.allclose(Xt, X[:, :2]))

    print("[A0-2] 장애인 내 정규화 (시행 내 정규화는 정의 불가)")
    z = patient_within_norm([10.0, 10.0])
    chk("분산 0 → 전부 0", np.allclose(z, [0.0, 0.0]), str(z))
    z2 = patient_within_norm([10.0, 20.0])
    chk("정규화 후 평균 0·표준편차 1", abs(z2.mean()) < 1e-9 and abs(z2.std() - 1) < 1e-9)

    print("[A0-3] 모델이 신호를 학습하는가 (합성)")
    rng = np.random.RandomState(0)
    n = 200
    K = rng.normal(0, 1, size=(n, 2))
    Xs = np.hstack([K, rng.normal(0, 0.1, size=(n, 8))])
    y = np.clip(np.round(1.5 + 1.2 * K[:, 0]), 0, 3).astype(int)
    Xtr, Xte = standardize(Xs[:150], Xs[150:])
    mdl = SoftmaxLR(Xtr.shape[1]).fit(Xtr, y[:150])
    acc = float(np.mean(mdl.predict(Xte) == y[150:]))
    chk("합성 학습 정확도 > 0.45 (무작위 0.25)", acc > 0.45, "acc=%.3f" % acc)

    print("[A0-4] 예측 스키마가 하네스와 호환")
    # ⚠️ 장애인 단위 2-fold 이므로 최소한 fold당 train > 클래스 수(4) 여야 한다.
    #    4명이면 train 2건 → 4-class 적합 불가로 건너뛴다(가드가 정상 작동).
    rr, ref = [], {}
    for i in range(12):
        pid = "P%02d" % i
        for t in range(3):
            tid = "%s_T1_t%d" % (pid, t + 1)
            rr.append(rec(pid + "_x", tid, 10.0 + i + 0.3 * t, 100.0 + 7 * i + 2 * t))
            ref[(pid + "_x", tid)] = min(3, (i + t) % 4)
    rows, mae = run(rr, ref, "A0", True, True, True, folds=2)
    chk("예측 행 생성됨 (12명×3시행)", len(rows) >= 30, "n=%d" % len(rows))
    chk("필드가 PRED_FIELDS 와 일치",
        all(set(r.keys()) == set(PRED_FIELDS) for r in rows))
    chk("점수가 0~3 정수",
        all(isinstance(r["score"], int) and 0 <= r["score"] <= 3 for r in rows))
    chk("MAE 산출됨(NaN 아님)", mae == mae, "mae=%.4f" % mae)

    print("[A0-5] A0 와 A0-time 분리")
    r0, m0 = run(rr, ref, "A0", True, True, True)
    r1, m1 = run(rr, ref, "A0time", False, False, True)
    chk("A0-time 은 조건명 A0time", bool(r1) and all(x["condition"] == "A0time" for x in r1),
        "n=%d" % len(r1))
    chk("A0 은 조건명 A0", bool(r0) and all(x["condition"] == "A0" for x in r0),
        "n=%d" % len(r0))

    print("")
    print("오라클 종합: %s" % ("ALL PASS" if ok_all else "FAIL 있음"))
    print("※ 합성 데이터다. 실제 예측 성능이 아니다.")
    try:
        outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "results", "baseline_oracle.txt")
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with io.open(outp, "w", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n")
        print("[saved] %s" % os.path.abspath(outp))
    except Exception as e:
        print("[warn] 로그 저장 실패: %s" % e)
    return ok_all


# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--l2", nargs="*", default=[], help="세션 폴더(들)")
    ap.add_argument("--reference", help="채점 CSV (session, trial_id, score)")
    ap.add_argument("--out", default="predictions_A0.csv")
    a = ap.parse_args()

    if a.selftest:
        return 0 if selftest() else 1
    if not a.l2 or not a.reference:
        print(__doc__)
        return 0

    recs = []
    for d in a.l2:
        recs += load_l2(d)
    if not recs:
        print("L2 레코드 0건"); return 1
    ref = load_reference(a.reference)

    rows0, mae0 = run(recs, ref, "A0", True, True, True)
    rows1, mae1 = run(recs, ref, "A0time", False, False, True)
    rows = rows0 + rows1
    write_predictions(rows, a.out)
    print("A0      n=%d  MAE=%.4f" % (len(rows0), mae0))
    print("A0-time n=%d  MAE=%.4f" % (len(rows1), mae1))
    print("→ %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
