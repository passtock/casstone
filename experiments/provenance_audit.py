#!/usr/bin/env python3
"""provenance_audit.py — 인용 식별자(PMID/PMCID/DOI/arXiv) 추출 + 외부 레코드 대조 검증

목적
----
워크스페이스의 Markdown 문서에 적힌 인용 식별자가 *실제로 존재하는 레코드*를
가리키는지, 그리고 그 레코드의 제목·연도가 문서에 적힌 서술과 일치하는지 확인한다.

사용
----
    python experiments/provenance_audit.py extract        # 식별자 + 문맥 추출
    python experiments/provenance_audit.py verify         # 외부 API 대조 (네트워크)
    python experiments/provenance_audit.py report         # 플래그 요약 출력

산출물 (outputs/03-검증/provenance/)
----
    _extracted.json      파일별 식별자 + 등장 문맥
    _unique_ids.json     고유 식별자 집합
    verification-results.json   식별자별 검증 결과

주의
----
- 읽기 전용. 어떤 문서도 수정하지 않는다.
- 외부 API: PubMed E-utilities / Crossref / arXiv / OpenAlex.
- arXiv export API는 이 환경에서 인증서 체인 검증 실패가 나므로
  해당 호스트만 unverified SSL context를 사용한다(읽기 전용 공개 메타데이터).
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "03-검증" / "provenance"
UA = {"User-Agent": "Feynman-Provenance-Audit/1.0 (research; mailto:research@example.org)"}

PAT_PMID = re.compile(r"PMID[:\s]*(\d{6,9})")
PAT_PMCID = re.compile(r"(PMC\d{6,9})")
# DOI는 괄호·세미콜론·쉼표를 포함할 수 있다(예: 10.1016/S0140-6736(86)90837-8).
# 따라서 비공백 런을 먼저 잡고 norm_doi에서 괄호 균형을 보며 꼬리를 벗긴다.
PAT_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>`]+)")
PAT_ARXIV = re.compile(r"(?:arXiv[:\s]*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})", re.I)

# 검증 우선순위: 사용자가 지목한 증거맵/아틀라스 + 정본 계획서
PRIORITY = [
    "outputs/01-조사문헌/arat-fma-ue-evidence-map.md",
    "outputs/01-조사문헌/rgbd-grasp-vlm-protocol-analysis.md",
    "outputs/research-plan-v6.md",
    "outputs/research-plan-v6-easy.md",
    "outputs/01-조사문헌/arat-fma-ue-evidence-map-ko.md",
    "outputs/protocol-v6-frozen.md",
    "outputs/02-설계이력/experiment-plan-v6-naive.md",
    "outputs/03-검증/systematic-search-novelty-audit.md",
]

SKIP_DIR_PARTS = (".git", "open-science-seeds", ".drafts", ".plans", ".feynman",
                 "_backup_terminology", "model-endpoints", "__pycache__")


def norm_doi(d: str) -> str:
    """DOI 추출 잡음 제거.

    Markdown 강조(**), 이스케이프(\\_), URL 접미사(/full, /pdf), 한국어 조사(로, 입니다),
    표 구분자(|), 꼬리 문장부호를 벗긴다. 벗긴 흔적은 호출자가 알 수 있게 남기지 않는다
    (원문확인은 문맥 파일이 담당).
    """
    d = d.strip()
    d = d.split("](")[0]  # Markdown 링크 꼬리 제거
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d, flags=re.I)
    d = d.replace("\\_", "_").replace("\\", "")
    d = d.replace("**", "").replace("*", "").replace("~", "")
    for _ in range(8):
        prev = d
        d = d.rstrip("|.,;:)]}· ")
        while d and d[-1] == ")" and d.count(")") > d.count("("):
            d = d[:-1]
        d = re.sub(r"(?:/(full|pdf|abstract|epdf|html?))+$", "", d, flags=re.I)
        d = re.sub(r"(입니다|으로|에서|에서는|이고|이며|로|은|는|이|가|와|과|에|을|를|도|만)$", "", d)
        if d == prev:
            break
    return d


def md_files() -> list[pathlib.Path]:
    out = []
    for p in ROOT.rglob("*.md"):
        s = p.as_posix()
        if any(part in s for part in SKIP_DIR_PARTS):
            continue
        out.append(p)
    return sorted(out)


def cmd_extract() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = md_files()
    per_file: dict[str, dict] = {}
    contexts: dict[str, dict[str, list[dict]]] = {}

    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        found = {
            "pmid": sorted(set(PAT_PMID.findall(text))),
            "pmcid": sorted(set(PAT_PMCID.findall(text))),
            "doi": sorted({norm_doi(x) for x in PAT_DOI.findall(text)}),
            "arxiv": sorted({x for x in PAT_ARXIV.findall(text)}),
        }
        if not any(found.values()):
            continue
        per_file[rel] = found
        ctx: dict[str, list[dict]] = {k: [] for k in found}
        for i, ln in enumerate(lines, 1):
            for uid in PAT_PMID.findall(ln):
                ctx["pmid"].append({"id": uid, "line": i, "text": ln.strip()[:400]})
            for uid in PAT_PMCID.findall(ln):
                ctx["pmcid"].append({"id": uid, "line": i, "text": ln.strip()[:400]})
            for uid in PAT_DOI.findall(ln):
                ctx["doi"].append({"id": norm_doi(uid), "line": i, "text": ln.strip()[:400]})
            for uid in PAT_ARXIV.findall(ln):
                ctx["arxiv"].append({"id": uid, "line": i, "text": ln.strip()[:400]})
        contexts[rel] = ctx

    unique = {k: sorted({x for d in per_file.values() for x in d[k]})
              for k in ("pmid", "pmcid", "doi", "arxiv")}
    (OUT / "_extracted.json").write_text(
        json.dumps(per_file, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "_contexts.json").write_text(
        json.dumps(contexts, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "_unique_ids.json").write_text(
        json.dumps(unique, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"scanned md files: {len(files)} | with identifiers: {len(per_file)}")
    print("unique:", {k: len(v) for k, v in unique.items()})
    print("priority files:")
    for rel in PRIORITY:
        if rel in per_file:
            d = per_file[rel]
            print(f"  {rel}: pmid={len(d['pmid'])} pmcid={len(d['pmcid'])} "
                  f"doi={len(d['doi'])} arxiv={len(d['arxiv'])}")
        else:
            print(f"  {rel}: (없음)")


def _get(url: str, timeout: int = 30, insecure: bool = False) -> tuple[int, str]:
    ctx = ssl._create_unverified_context() if insecure else None
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as f:
        return f.status, f.read().decode("utf-8", "replace")


def _sim(a: str, b: str) -> float:
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def verify_pubmed(ids: list[str], results: dict) -> None:
    """PubMed esummary — 배치(최대 200)."""
    for i in range(0, len(ids), 150):
        chunk = ids[i:i + 150]
        url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
               f"?db=pubmed&id={','.join(chunk)}&retmode=json")
        try:
            _, body = _get(url)
            js = json.loads(body)
            res = js.get("result", {})
            for pid in chunk:
                rec = res.get(pid)
                if not isinstance(rec, dict):
                    results.setdefault("pmid", {})[pid] = {"exists": False, "source": "pubmed/esummary"}
                    continue
                if rec.get("error"):
                    results.setdefault("pmid", {})[pid] = {"exists": False, "error": rec["error"],
                                                           "source": "pubmed/esummary"}
                    continue
                results.setdefault("pmid", {})[pid] = {
                    "exists": True,
                    "title": rec.get("title", ""),
                    "year": (rec.get("pubdate") or "")[:4],
                    "journal": rec.get("fulljournalname") or rec.get("source", ""),
                    "first_author": (rec.get("authors") or [{}])[0].get("name", ""),
                    "doi": next((x["value"] for x in rec.get("articleids", []) if x["idtype"] == "doi"), ""),
                    "source": "pubmed/esummary",
                }
        except Exception as e:  # noqa: BLE001
            for pid in chunk:
                results.setdefault("pmid", {})[pid] = {"exists": None, "error": str(e),
                                                       "source": "pubmed/esummary"}
        time.sleep(0.4)


def verify_pmcid(ids: list[str], results: dict) -> None:
    for pid in ids:
        url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
               f"?db=pmc&id={pid[3:]}&retmode=json")
        try:
            _, body = _get(url)
            rec = json.loads(body).get("result", {}).get(pid[3:])
            if isinstance(rec, dict) and not rec.get("error"):
                results.setdefault("pmcid", {})[pid] = {
                    "exists": True, "title": rec.get("title", ""),
                    "doi": rec.get("doi", ""), "source": "pmc/esummary"}
            else:
                results.setdefault("pmcid", {})[pid] = {"exists": False, "source": "pmc/esummary"}
        except Exception as e:  # noqa: BLE001
            results.setdefault("pmcid", {})[pid] = {"exists": None, "error": str(e),
                                                    "source": "pmc/esummary"}
        time.sleep(0.35)


def verify_doi(ids: list[str], results: dict) -> None:
    for d in ids:
        entry = {"source": "crossref/works"}
        try:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(d)}?mailto=research@example.org"
            _, body = _get(url)
            m = json.loads(body)["message"]
            entry.update({
                "exists": True,
                "title": (m.get("title") or [""])[0],
                "year": str((m.get("issued", {}).get("date-parts") or [[""]])[0][0] or ""),
                "journal": (m.get("container-title") or [""])[0],
                "first_author": (
                    f"{m.get('author', [{}])[0].get('family', '')} "
                    f"{m.get('author', [{}])[0].get('given', '')}".strip()
                    if m.get("author") else ""),
                "type": m.get("type", ""),
            })
        except urllib.error.HTTPError as e:
            entry.update({"exists": False if e.code == 404 else None,
                          "http": e.code})
        except Exception as e:  # noqa: BLE001
            entry.update({"exists": None, "error": str(e)})

        # Crossref에 없어도 DataCite 등록(Zenodo 등)일 수 있다 → doi.org 해석으로 2차 확인
        if entry.get("exists") is not True:
            try:
                req = urllib.request.Request(
                    "https://doi.org/api/handles/" + urllib.parse.quote(d), headers=UA)
                with urllib.request.urlopen(req, timeout=25) as f:
                    h = json.loads(f.read().decode("utf-8", "replace"))
                if h.get("responseCode") == 1:
                    entry["exists"] = True
                    entry["resolved_by"] = "doi.org/handles"
                    entry["handle_url"] = next(
                        (v["data"]["value"] for v in h.get("values", [])
                         if v.get("type") == "URL"), "")
            except Exception as e:  # noqa: BLE001
                entry.setdefault("handle_probe", str(e))

        results.setdefault("doi", {})[d] = entry
        time.sleep(0.15)


def verify_arxiv(ids: list[str], results: dict) -> None:
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        url = ("https://export.arxiv.org/api/query?id_list=" + ",".join(chunk)
               + "&max_results=60")
        try:
            _, body = _get(url, insecure=True)
            # 최소 파싱: <entry> 블록에서 id/title/published 뽑기
            entries = re.findall(r"<entry>(.*?)</entry>", body, re.S)
            by_id: dict[str, dict] = {}
            for e in entries:
                m = re.search(r"<id>https?://arxiv\.org/abs/([^<]+)</id>", e)
                if not m:
                    continue
                raw = m.group(1)
                base = re.sub(r"v\d+$", "", raw)
                title = re.sub(r"\s+", " ", re.search(r"<title>(.*?)</title>", e, re.S).group(1)).strip()
                pub = re.search(r"<published>(\d{4})", e).group(1)
                auth = re.findall(r"<name>([^<]+)</name>", e)
                by_id[base] = {"exists": True, "title": title, "year": pub,
                               "first_author": auth[0] if auth else "",
                               "version": raw if raw != base else "",
                               "source": "arxiv/api"}
            for a in chunk:
                results.setdefault("arxiv", {})[a] = by_id.get(
                    a, {"exists": False, "source": "arxiv/api"})
        except Exception as e:  # noqa: BLE001
            for a in chunk:
                results.setdefault("arxiv", {})[a] = {"exists": None, "error": str(e),
                                                      "source": "arxiv/api"}
        time.sleep(3.0)  # arXiv 예절


def cmd_verify() -> None:
    uniq = json.loads((OUT / "_unique_ids.json").read_text(encoding="utf-8"))
    results: dict = {}
    print(f"verifying PMID {len(uniq['pmid'])} | PMCID {len(uniq['pmcid'])} | "
          f"DOI {len(uniq['doi'])} | arXiv {len(uniq['arxiv'])}")
    verify_pubmed(uniq["pmid"], results)
    print("  pubmed done")
    verify_pmcid(uniq["pmcid"], results)
    print("  pmc done")
    verify_doi(uniq["doi"], results)
    print("  crossref done")
    verify_arxiv(uniq["arxiv"], results)
    print("  arxiv done")
    (OUT / "verification-results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    missing = {k: [i for i, v in d.items() if v.get("exists") is False]
               for k, d in results.items()}
    print("\nNOT FOUND:")
    for k, v in missing.items():
        print(f"  {k} ({len(v)}): {v}")


def cmd_report() -> None:
    """식별자별로 '문서에 적힌 문맥' vs '실제 레코드'를 나란히 출력."""
    res = json.loads((OUT / "verification-results.json").read_text(encoding="utf-8"))
    ctx = json.loads((OUT / "_contexts.json").read_text(encoding="utf-8"))

    # id -> 등장 문맥(우선 파일 우선)
    idx: dict[str, dict[str, list[dict]]] = {}
    for rel, per in ctx.items():
        for kind, lst in per.items():
            for e in lst:
                idx.setdefault(kind, {}).setdefault(e["id"], []).append({"file": rel, **e})

    print("=" * 100)
    print("NOT FOUND / ERROR")
    print("=" * 100)
    for kind, d in res.items():
        for uid, v in d.items():
            if v.get("exists") is not True:
                where = idx.get(kind, {}).get(uid, [])
                print(f"\n[{kind}] {uid} -> exists={v.get('exists')} {v.get('error', '') or v.get('http', '')}")
                for w in where[:4]:
                    print(f"    {w['file']}:{w['line']}  {w['text'][:180]}")

    print()
    print("=" * 100)
    print("TITLE MISMATCH (문서 제목 vs 실제 제목, 유사도 < 0.55)")
    print("=" * 100)
    for kind in ("doi", "arxiv", "pmid"):
        for uid, v in res.get(kind, {}).items():
            if v.get("exists") is not True:
                continue
            real = v.get("title", "")
            if not real:  # DataCite/handle로만 확인된 건 제목 비교 불가
                continue
            for w in idx.get(kind, {}).get(uid, [])[:3]:
                txt = w["text"]
                if real and _sim(real, txt) < 0.55:
                    print(f"\n[{kind}] {uid} sim={_sim(real, txt):.2f}")
                    print(f"  REAL : {real[:150]}")
                    print(f"  DOC  : {w['file']}:{w['line']}  {txt[:190]}")
                    break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "verify", "report"])
    a = ap.parse_args()
    {"extract": cmd_extract, "verify": cmd_verify, "report": cmd_report}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
