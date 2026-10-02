"""Audit v15 claims without modifying prior code or results."""
from pathlib import Path
import sys, json, importlib.util, contextlib, io, hashlib
import numpy as np
import pandas as pd
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'호진파일/outputs/데이터_저장'
EXP=BASE.parent/'experiments'
OUT=BASE/'outputs/independent_hand_review_20261002/v15_followup'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(EXP/'metrics'))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
m4=load('review_m4',EXP/'v15/m4_definition_review.py')
inj=load('review_injection',EXP/'v15/failure_injection.py')
port=load('review_portfolio',EXP/'v15/portfolio_v132_unified.py')
before={str(p):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in (EXP/'v15').glob('*.py')}
for module,name in ((m4,'original_m4_reproduced.json'),(inj,'original_injection_reproduced.json')):
    module.ROOT=str(DATA); module.OUT=str(OUT/name)
    with contextlib.redirect_stdout(io.StringIO()): module.main()

def standard_ldlj(speed,t):
    speed=np.asarray(speed,float); t=np.asarray(t,float)
    dt=float(t[1]-t[0]); T=float(t[-1]-t[0])
    peak=float(np.max(np.abs(speed)))
    jerk=np.gradient(np.gradient(speed,dt),dt)
    return float(-np.log(T**3/peak**2*np.sum(jerk**2)*dt))
t=np.linspace(0,1,1001); v=np.exp(-((t-.5)/.17)**2)
tests={'original_ldlj':{'one_second':m4.ldlj(v,t),'two_seconds_same_shape':m4.ldlj(v/2,t*2)},
       'second_derivative_reference':{'one_second':standard_ldlj(v,t),'two_seconds_same_shape':standard_ldlj(v/2,t*2)}}
tests['original_ldlj']['duration_change']=tests['original_ldlj']['two_seconds_same_shape']-tests['original_ldlj']['one_second']
tests['second_derivative_reference']['duration_change']=tests['second_derivative_reference']['two_seconds_same_shape']-tests['second_derivative_reference']['one_second']
assert np.isclose(tests['original_ldlj']['duration_change'],-2*np.log(2))
assert np.isclose(tests['second_derivative_reference']['duration_change'],0)

# Anatomical definition: CMC(1)-MCP(2)-IP(3), MCP(2)-IP(3)-TIP(4).
definitions={'prior_thumb':m4.FLEX14[:2],'planned_thumb':[(1,2,3),(2,3,4)]}
struct=[]; baseline=[]; paired=[]
PF={}
for d in sorted(x for x in DATA.iterdir() if x.is_dir()):
    ts=pd.read_csv(next(d.glob('Session_*_trials_summary.csv')))
    same=all(g.Start_s.nunique()==1 and g.End_s.nunique()==1 and len(g)==2 for _,g in ts.groupby('Trial'))
    struct.append({'session':d.name,'rows':len(ts),'windows':ts.Trial.nunique(),'left_right_same_window':same})
    for h in ('Left','Right'):
        wins=inj.load_windows(str(d),h)
        PF[(d.name,h)]=[inj.per_frame(w['P'],w['t']) for w in wins]
        prior_metrics=port.trial_metrics(str(d),h)
        old=port.FLEX14
        port.FLEX14={'Thumb_MCP':(1,2,3),'Thumb_IP':(2,3,4),**{k:v for k,v in old.items() if not k.startswith('Thumb')}}
        corrected=port.trial_metrics(str(d),h)
        port.FLEX14=old
        changes=[b['F_sum14_p95_deg']-a['F_sum14_p95_deg'] for a,b in zip(prior_metrics,corrected)]
        paired.append({'session':d.name,'hand':h,'n':len(changes),'correct_minus_original_fsum14_median':float(np.median(changes)),
                       'min':min(changes),'max':max(changes)})
for (s,h),pfs in PF.items():
    others=[p for (other_s,other_h),rows in PF.items() if other_s!=s for p in rows]
    kappa=inj.fit_kappa(others)
    for pf in pfs:
        a,b=inj.rule_current(pf),inj.rule_B(pf,kappa)
        baseline.append({'session':s,'hand':h,'n_frames':pf['F'],'current_any':bool(a.any()),'current_rate':float(a.mean()),
                         'current_over_30pct':bool(a.mean()>.3),'B_any':bool(b.any()),'B_rate':float(b.mean()),'B_over_30pct':bool(b.mean()>.3)})
base_df=pd.DataFrame(baseline)
gate_summary=base_df.groupby(['session','hand']).agg(n=('n_frames','size'),current_any=('current_any','sum'),current_over_30pct=('current_over_30pct','sum'),B_any=('B_any','sum'),B_over_30pct=('B_over_30pct','sum')).reset_index().to_dict('records')

# On a stable complete skeleton, single fingertip corruption reaches only one segment.
rng=np.random.default_rng(3); P=np.tile(rng.normal(scale=.03,size=(21,3)),(100,1,1)); clock=np.arange(100)*.05
synthetic=[]
for kind in ('I1_jump','I2_loss','I3_scale','I4_collapse'):
    Q,sl=inj.inject(P,kind,40,8,np.random.default_rng(5))
    flags=inj.rule_current(inj.per_frame(Q,clock))
    synthetic.append({'kind':kind,'baseline_flags':int(inj.rule_current(inj.per_frame(P,clock)).sum()),'injected_flags':int(flags[sl].sum()),'injection_frames':8})

summary={'structural_windows':struct,'ldlj_time_scaling_test':tests,'thumb_definitions':definitions,'thumb_correction_effects':paired,
         'per_session_gate_counts_diagnostic_only':gate_summary,'unmodified_flag_rate_not_false_alarm':baseline,
         'single_tip_injection_tests':synthetic,
         'original_reported_result_keys':list(json.loads((OUT/'original_injection_reproduced.json').read_text(encoding='utf8'))['false_alarm']),
         'actual_windows_evaluated':sum(len(pfs) for (s,h),pfs in PF.items() if h=='Left'),
         'actual_hand_rows_evaluated':sum(map(len,PF.values()))}
(OUT/'v15_independent_checks.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
assert all(hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()==h for p,h in before.items())
print(json.dumps({'time_scaling':tests,'windows':summary['actual_windows_evaluated'],'hand_rows':summary['actual_hand_rows_evaluated'],
                 'gate_summary':gate_summary,'synthetic':synthetic,'thumb_effects':paired},ensure_ascii=False,indent=2))
