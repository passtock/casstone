"""Reproduce the established plots for Choi; all nine trials per session."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
LAST_SIX='--last-six' in sys.argv
CUSTOM='--exclude-before-1-4-7-8' in sys.argv
assert not (LAST_SIX and CUSTOM)
OUT=ROOT/'outputs'/('choi_byungho_before5_after9_20261006' if CUSTOM else ('choi_byungho_last6_comparison_20261006' if LAST_SIX else 'choi_byungho_comparison_20261006'))
OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'호진파일'/'outputs'/'데이터_저장'
folders={'Before':DATA/'20261006_환자_최병호_59세_남_FMA12_BRS4 - 복사본',
         'After':DATA/'20261006_환자_최병호애프터_59세_남_FMA12_BRS4 - 복사본'}
sources={s:str(next(p.glob('*continuous_raw.csv'))) for s,p in folders.items()}
(OUT/'analysis.json').write_text(json.dumps({'sources':sources},ensure_ascii=False,indent=2),encoding='utf-8')

extension=(ROOT/'plot_extension_20261006.py').read_text(encoding='utf-8')
# Keep dependencies in their original location; only change the result folder.
extension=extension.replace("OUT = ROOT / 'outputs' / 'extension_comparison_20261006'","OUT = ROOT / 'outputs' / 'choi_byungho_comparison_20261006'")
extension=extension.replace("    if session=='After': rows=rows[rows.Trial.ne('Trial_3')]\n",'')
extension=extension.replace("    assert session!='After' or 'Trial_3' not in trials.index.get_level_values('Trial')\n",'')
extension=extension.replace('(7 if session==\'Before\' else 8)','9')
extension=extension.replace('before_n=7,after_n=8','before_n=9,after_n=9')
extension=extension.replace("'After Trial_3: recording error, user confirmed'","'None: all recorded trials included'")
extension=extension.replace("'n_before':7,'n_after':8","'n_before':9,'n_after':9")
extension=extension.replace("['Left','Right']","['Right','Left']")
extension=extension.replace("'환측 · 왼손' if hand=='Left' else '비마비측 · 오른손'","'환측 · 오른손' if hand=='Right' else '비마비측 · 왼손'")
extension=extension.replace('전 7회 · 후 8회','전 9회 · 후 9회').replace('후 Trial 3 제외','전체 시행 포함')
extension=extension.replace('미러테라피 전후 최대 신전각도','최병호님 · 미러테라피 전후 최대 신전각도')
extension=extension.replace('관절별 최고 피크 신전각도','최병호님 · 관절별 최고 피크 신전각도')
extension=extension.replace('after_trial3_excluded','all_trials')
extension=extension.replace('ax.set_xlim(137,182)',"ax.set_xlim(np.floor(min(df.before_mean_deg-df.before_sd_deg)/10)*10-5,182)")
extension=extension.replace('ax.set_xlim(140,182)',"ax.set_xlim(np.floor(min(df.before_peak_deg.min(),df.after_peak_deg.min())/10)*10-5,182)")
extension=extension.replace('delta.set_xlim(-10.5,6.4)',"delta.set_xlim(min(-10.5,df.change_deg.min()-2),max(6.4,df.change_deg.max()+2))")
extension=extension.replace('ax.set_xticks([140,150,160,170,180])','ax.set_xticks([90,105,120,135,150,165,180])')
extension=extension.replace('delta.set_xticks([-10,-5,0,5])','delta.set_xticks([-10,-5,0,5,10])')
if LAST_SIX:
    extension=extension.replace("'choi_byungho_comparison_20261006'","'choi_byungho_last6_comparison_20261006'")
    extension=extension.replace('    cols=[j+',"    rows=rows[rows.Trial.isin([f'Trial_{i}' for i in range(4,10)])]\n    cols=[j+")
    extension=extension.replace('== 9','== 6').replace('before_n=9,after_n=9','before_n=6,after_n=6')
    extension=extension.replace("'n_before':9,'n_after':9","'n_before':6,'n_after':6")
    extension=extension.replace('None: all recorded trials included','Before and After Trial_1 to Trial_3 excluded; last six trials retained')
    extension=extension.replace('전 9회 · 후 9회','전 6회 · 후 6회').replace('전체 시행 포함','각 세션의 마지막 6회 (Trial 4~9)')
    extension=extension.replace('all_trials','last_six_trials')
elif CUSTOM:
    extension=extension.replace("'choi_byungho_comparison_20261006'","'choi_byungho_before5_after9_20261006'")
    extension=extension.replace('    cols=[j+',"    if session=='Before': rows=rows[~rows.Trial.isin(['Trial_1','Trial_4','Trial_7','Trial_8'])]\n    cols=[j+")
    extension=extension.replace('== 9',"== (5 if session=='Before' else 9)")
    extension=extension.replace('before_n=9,after_n=9','before_n=5,after_n=9')
    extension=extension.replace("'n_before':9,'n_after':9","'n_before':5,'n_after':9")
    extension=extension.replace('None: all recorded trials included','Before Trial_1, Trial_4, Trial_7, Trial_8 excluded by user; After all trials retained')
    extension=extension.replace('전 9회 · 후 9회','전 5회 · 후 9회').replace('전체 시행 포함','전 Trial 1·4·7·8 제외 / 후 전체 포함')
    extension=extension.replace('all_trials','before5_after9')
exec(compile(extension,'choi_extension_plot','exec'),{'__file__':str(ROOT/'plot_extension_20261006.py'),'__name__':'__main__'})

functional=(ROOT/'plot_functional_metrics_20261006.py').read_text(encoding='utf-8')
functional=functional.replace("OUT=ROOT/'outputs'/'extension_comparison_20261006'","OUT=ROOT/'outputs'/'choi_byungho_comparison_20261006'")
functional=functional.replace("sys.path.insert(0,str(OUT/'plot_dependencies'))","sys.path.insert(0,str(ROOT/'outputs'/'extension_comparison_20261006'/'plot_dependencies'))")
functional=functional.replace("    if session=='After':df=df[df.Trial.ne('Trial #3')]\n",'')
functional=functional.replace("    if session=='After':frames=frames[frames.Trial.ne('Trial_3')]\n",'')
functional=functional.replace("(7 if session=='Before' else 8)",'9')
functional=functional.replace("['Left','Right']","['Right','Left']")
functional=functional.replace("r.hand=='Left'","r.hand=='Right'")
functional=functional.replace("['환측(좌)','비마비측(우)']","['환측(우)','비마비측(좌)']")
functional=functional.replace('전 7회 · 후 8회','전 9회 · 후 9회').replace('잘못 녹화된 후 Trial 3 제외','전체 시행 포함')
functional=functional.replace('미러테라피 전후 손 벌림·운동학 지표','최병호님 · 손 벌림·운동학 지표 전후 비교')
functional=functional.replace('after_trial3_excluded','all_trials')
if LAST_SIX:
    functional=functional.replace("'choi_byungho_comparison_20261006'","'choi_byungho_last6_comparison_20261006'")
    functional=functional.replace('    # Verify nonvelocity',"    df=df[df.Trial.isin([f'Trial #{i}' for i in range(4,10)])]\n    assert all(len(df[df.Hand.eq(h)])==6 for h in ['Right','Left'])\n    data[session]=df\n    # Verify nonvelocity")
    functional=functional.replace('전 9회 · 후 9회','전 6회 · 후 6회').replace('전체 시행 포함','각 세션의 마지막 6회 (Trial 4~9)')
    functional=functional.replace('all_trials','last_six_trials')
elif CUSTOM:
    functional=functional.replace("'choi_byungho_comparison_20261006'","'choi_byungho_before5_after9_20261006'")
    functional=functional.replace('    assert all(len(df',"    if session=='Before': df=df[~df.Trial.isin(['Trial #1','Trial #4','Trial #7','Trial #8'])]\n    assert all(len(df")
    functional=functional.replace('==9',"==(5 if session=='Before' else 9)")
    functional=functional.replace('전 9회 · 후 9회','전 5회 · 후 9회').replace('전체 시행 포함','전 Trial 1·4·7·8 제외 / 후 전체 포함')
    functional=functional.replace('all_trials','before5_after9')
exec(compile(functional,'choi_functional_plot','exec'),{'__file__':str(ROOT/'plot_functional_metrics_20261006.py'),'__name__':'__main__'})
