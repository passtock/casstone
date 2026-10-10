# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\passp\Desktop\univercity\4-2\캡스톤\capstone\호진파일\outputs\데이터_저장\full_3patients_analysis.json', 'r', encoding='utf-8') as fp:
    res = json.load(fp)

for name, s in res.items():
    print('='*75)
    print(f'환자: {name}')
    aff = s['affected']
    unaff = s['unaffected']
    
    print('  [환측(Affected) 15개 관절 신전각 평균 및 총합]')
    ov_m = aff['overall']['mean_deg']
    ov_s = aff['overall']['sum_deg']
    print(f'    15개 관절 평균각: Before={ov_m["before_mean"]:.2f}°, After={ov_m["after_mean"]:.2f}°, Delta={ov_m["delta"]:+.2f}°')
    print(f'    15개 관절 합산각: Before={ov_s["before_mean"]:.2f}°, After={ov_s["after_mean"]:.2f}°, Delta={ov_s["delta"]:+.2f}°')
    
    print('  [환측 손가락별 신전각 합계]')
    for f, fstat in aff['fingers'].items():
        print(f'    {f:6s}: Before={fstat["before_mean"]:6.2f}°, After={fstat["after_mean"]:6.2f}°, Delta={fstat["delta"]:+.2f}°')
        
    print('  [환측 기능 및 운동학 지표]')
    for k, v in s['trials_metrics'].items():
        print(f'    {k:24s}: Before={v["before_mean"]:7.2f}, After={v["after_mean"]:7.2f}, Delta={v["delta"]:+6.2f} ({v["pct_change"]:+6.1f}%), d={v["cohen_d"]:+5.2f}, p={v["p_val"]:.4f}')

    print('  [환측 15개 관절별 주요 유의미 변화]')
    for j, jstat in aff['joints'].items():
        if abs(jstat['delta_mean']) >= 1.0 or jstat['p_val'] < 0.1:
            sig = '*' if jstat['p_val'] < 0.05 else ('.' if jstat['p_val'] < 0.1 else '')
            print(f'    {j:15s}: Before={jstat["before_mean"]:6.2f}°, After={jstat["after_mean"]:6.2f}°, Delta={jstat["delta_mean"]:+5.2f}°, Peak={jstat["delta_peak"]:+5.2f}°, d={jstat["cohen_d"]:+5.2f}, p={jstat["p_val"]:.4f}{sig}')
