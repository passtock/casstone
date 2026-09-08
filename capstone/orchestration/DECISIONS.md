# 운영 결정 기록

## 2026-09-08 — 초기 모델 배치
- 사용자 요청: 캡스톤 폴더 안에 역할별 모델을 선정하고 설정.
- 총괄 및 연구설계: GPT-6 Astra / high.
- 실험구현: GPT-5.6 Sol / high.
- 발표: GPT-5.6 Sol / medium.
- 이유: 연구 판단에는 Astra를 배치하고, 구현 및 산출물 제작은 Sol로 시작한다. 실측 성능 비교에 따른 확정 순위는 아니다.
- 동시 담당자 상한: 3명. 단계 의존성이 있으면 순차 실행.
- 기존 자료는 이동하거나 수정하지 않는다.
- 근거: https://learn.chatgpt.com/docs/agent-configuration/subagents
- 모델 참고: https://developers.openai.com/api/docs/guides/latest-model
- Sol 참고: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6
- Terra 참고: https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6-terra

## 2026-09-08 — 슬기로운 통계생활(AA v4.2) 벤치마크 분석 기반 모델 최적화 재설정
- 참고 분석: https://statisticsplaybook.com/gpt-6-astra-vs-gpt-5-6-sol/
- 분석 핵심 결과:
  1. 지능 지수(AA v4.2): Astra low(49) ≈ Sol high(48), Astra medium(52) > Sol xhigh(50)/max(51). Astra는 한 단계 낮은 추론으로도 Sol 상위급 점수를 기록.
  2. 토큰 절감률: Astra low는 Sol high 대비 출력 토큰 77.5% 절약(5.4M vs 24M), Astra medium은 Sol xhigh 대비 70% 절약(12M vs 40M).
  3. 응답 속도: 첫 응답 대기 시간에서 Astra medium(17.88초)이 Sol xhigh(70.10초)보다 약 4배 빠름. 순수 텍스트 생성 속도는 Sol(82 tok/s)이 우위.
  4. 도구/명령어 실행: Terminal-Bench(57.9% vs 37.3%), AutomationBench(41.4% vs 18.1%)에서 Astra가 20%p 이상 압도.
  5. 사용량 한도(Rate limit): Sol ultra는 과도한 추론 토큰 소모로 Plus 한도를 급격히 소진(112만 토큰 초과 에러 원인).
- 재배치 구성:
  - 총괄: GPT-6 Astra / medium (에이전트 지휘, 도구 조율 및 요약 최적화)
  - 연구설계(research_planner): GPT-6 Astra / medium (high 대비 토큰 37% 절약하면서도 52점 고지능 유지)
  - 실험구현(experiment_engineer): GPT-5.6 Sol / high (초기 검토)
  - 발표/문서작성(presentation_builder): GPT-5.6 Sol / medium (초기 검토)

## 2026-09-08 — ChatGPT Pro 환경 맞춤 전면 Astra 전환 (Sol → Astra low)
- 사용자 결정: ChatGPT Pro(월 정액) 환경에서는 API 비용보다 5시간당 메시지/토큰 한도 관리가 핵심이므로, Sol 모델을 모두 Astra low로 전면 전환.
- 근거:
  1. 토큰 대폭 절감: Astra low는 Sol high 대비 출력 토큰 약 77.5% 절약(5.4M vs 24M)으로 한도 소진을 극적으로 지연시킴.
  2. 성능 동등 이상: AA v4.2 기준 Astra low(49점)는 Sol high(48점) 이상이며, Terminal-Bench(+20.6%p)에서 도구 실행력 압도.
  3. 빠른 대기 시간: 응답 시간 10.72초 대 24.68초로 긴 추론 대기 없이 즉각적인 도구 호출 및 결과 확인 가능.
- 최종 확정 모델 프로필:
  - 총괄: GPT-6 Astra / medium
  - 연구설계(research_planner): GPT-6 Astra / medium
  - 실험구현(experiment_engineer): GPT-6 Astra / low
  - 발표/문서작성(presentation_builder): GPT-6 Astra / low



