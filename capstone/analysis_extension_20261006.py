from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / '호진파일' / 'outputs' / '데이터_저장'
DIRS = {'Before': DATA / '20260929_환자_권미사_62세_여_FMA11_BRS1 - 복사본',
        'After': DATA / '20260929_환자_권미사애프터_62세_여_FMA11_BRS1 - 복사본'}
JOINTS = ['Thumb_CMC','Thumb_MCP','Thumb_IP'] + [f'{f}_{j}' for f in ['Index','Middle','Ring','Pinky'] for j in ['MCP','PIP','DIP']]
frames = {}
peaks = {}
for session, folder in DIRS.items():
    raw = pd.read_csv(next(folder.glob('*continuous_raw.csv')))
    rows = raw[raw.Trial.str.startswith('Trial_') & raw.Protocol_Valid.eq(1)].copy()
    assert not rows.duplicated(['Trial','hand','Frame_ID']).any()
    frames[session] = rows
    for suffix in ['filt','raw','3D']:
        cols = [f'{j}_{suffix}' for j in JOINTS]
        assert rows[cols].notna().all().all()
        assert rows[cols].ge(0).all().all() and rows[cols].le(180).all().all()
        trial = rows.groupby(['hand','Trial'])[cols].max()
        trial.columns = JOINTS
        peaks[(session,suffix)] = trial

def compare(suffix='filt', omit_short=False):
    result=[]
    for hand in ['Left','Right']:
        b=peaks[('Before',suffix)].loc[hand]
        a=peaks[('After',suffix)].loc[hand]
        if omit_short: a=a.drop('Trial_3')
        for joint in JOINTS:
            result.append({'hand':hand,'joint':joint,'before_n':len(b),'after_n':len(a),
                'before_mean':b[joint].mean(),'before_sd':b[joint].std(),
                'after_mean':a[joint].mean(),'after_sd':a[joint].std(),
                'delta':a[joint].mean()-b[joint].mean(),
                'before_peak':b[joint].max(),'after_peak':a[joint].max()})
        result.append({'hand':hand,'joint':'Overall15','before_n':len(b),'after_n':len(a),
            'before_mean':b.mean(axis=1).mean(),'before_sd':b.mean(axis=1).std(),
            'after_mean':a.mean(axis=1).mean(),'after_sd':a.mean(axis=1).std(),
            'delta':a.mean(axis=1).mean()-b.mean(axis=1).mean(),
            'before_peak':None,'after_peak':None})
    return result

output={'sources':{s:str(next(p.glob('*continuous_raw.csv'))) for s,p in DIRS.items()},
    'primary':compare(), 'without_after_trial3':compare(omit_short=True),
    'three_d':compare('3D'), 'unfiltered':compare('raw'),
    'trials':{s:peaks[(s,'filt')].reset_index().to_dict(orient='records') for s in DIRS},
    'sample_counts':{s:frames[s].groupby(['hand','Trial']).size().to_dict() for s in DIRS}}
output['sample_counts']={s:{f'{h}/{t}':v for (h,t),v in x.items()} for s,x in output['sample_counts'].items()}
outdir=ROOT/'outputs'/'extension_comparison_20261006'
outdir.mkdir(parents=True,exist_ok=True)
(outdir/'analysis.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
for key in ['primary','without_after_trial3','three_d','unfiltered']:
    print('\n'+key)
    print(pd.DataFrame(output[key]).round(2).to_string(index=False))
