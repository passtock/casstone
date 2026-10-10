# -*- coding: utf-8 -*-
import os, glob, json, sys
import numpy as np
import pandas as pd
from scipy import stats

base = r'C:\Users\passp\Desktop\univercity\4-2\캡스톤\capstone\호진파일\outputs\데이터_저장'

subjects = {
    '권미사': {
        'age': 62, 'gender': '여', 'fma': 11, 'brs': 1, 'affected': 'Left', 'unaffected': 'Right',
        'before_dir': '20260929_환자_권미사_62세_여_FMA11_BRS1 - 복사본',
        'after_dir': '20260929_환자_권미사애프터_62세_여_FMA11_BRS1 - 복사본'
    },
    '최병호': {
        'age': 59, 'gender': '남', 'fma': 12, 'brs': 4, 'affected': 'Right', 'unaffected': 'Left',
        'before_dir': '20261006_환자_최병호_59세_남_FMA12_BRS4 - 복사본',
        'after_dir': '20261006_환자_최병호애프터_59세_남_FMA12_BRS4 - 복사본'
    },
    '정해교': {
        'age': 78, 'gender': '남', 'fma': 10, 'brs': 4, 'affected': 'Right', 'unaffected': 'Left',
        'before_dir': '20261008_환자_정해교_78세_남_FMA10_BRS4 - 복사본',
        'after_dir': '20261008_환자_정해교(애프터)_78세_남_FMA10_BRS4 - 복사본'
    }
}

JOINTS = ['Thumb_CMC','Thumb_MCP','Thumb_IP'] + [f'{f}_{j}' for f in ['Index','Middle','Ring','Pinky'] for j in ['MCP','PIP','DIP']]
FINGERS = {
    'Thumb': ['Thumb_CMC', 'Thumb_MCP', 'Thumb_IP'],
    'Index': ['Index_MCP', 'Index_PIP', 'Index_DIP'],
    'Middle': ['Middle_MCP', 'Middle_PIP', 'Middle_DIP'],
    'Ring': ['Ring_MCP', 'Ring_PIP', 'Ring_DIP'],
    'Pinky': ['Pinky_MCP', 'Pinky_PIP', 'Pinky_DIP']
}

results = {}

for name, sinfo in subjects.items():
    p_b = os.path.join(base, sinfo['before_dir'])
    p_a = os.path.join(base, sinfo['after_dir'])
    
    raw_b = pd.read_csv(glob.glob(os.path.join(p_b, '*continuous_raw.csv'))[0])
    raw_a = pd.read_csv(glob.glob(os.path.join(p_a, '*continuous_raw.csv'))[0])
    
    t_b = pd.read_csv(glob.glob(os.path.join(p_b, '*trials_summary.csv'))[0])
    t_a = pd.read_csv(glob.glob(os.path.join(p_a, '*trials_summary.csv'))[0])
    
    # Filter valid rows
    rows_b = raw_b[raw_b.Trial.str.startswith('Trial_') & raw_b.Protocol_Valid.eq(1)].copy()
    rows_a = raw_a[raw_a.Trial.str.startswith('Trial_') & raw_a.Protocol_Valid.eq(1)].copy()
    
    # Check trial peak extension angles
    cols_filt = [f'{j}_filt' for j in JOINTS]
    
    peaks_b = rows_b.groupby(['hand', 'Trial'])[cols_filt].max()
    peaks_b.columns = JOINTS
    
    peaks_a = rows_a.groupby(['hand', 'Trial'])[cols_filt].max()
    peaks_a.columns = JOINTS
    
    results[name] = {
        'info': sinfo,
        'peaks_b': peaks_b,
        'peaks_a': peaks_a,
        't_b': t_b,
        't_a': t_a,
        'rows_b': rows_b,
        'rows_a': rows_a
    }

# Compute statistics
analysis_output = {}

for name, data in results.items():
    aff = data['info']['affected']
    unaff = data['info']['unaffected']
    
    subj_res = {'affected': {}, 'unaffected': {}, 'trials_metrics': {}}
    
    for hand_label, hand_side in [('affected', aff), ('unaffected', unaff)]:
        pb = data['peaks_b'].loc[hand_side]
        pa = data['peaks_a'].loc[hand_side]
        
        # Joint by joint
        j_stats = {}
        for j in JOINTS:
            b_vals = pb[j].values
            a_vals = pa[j].values
            
            b_mean, b_std, b_max = np.mean(b_vals), np.std(b_vals, ddof=1), np.max(b_vals)
            a_mean, a_std, a_max = np.mean(a_vals), np.std(a_vals, ddof=1), np.max(a_vals)
            delta_mean = a_mean - b_mean
            delta_max = a_max - b_max
            
            # t-test (if equal length paired, else ind)
            if len(b_vals) == len(a_vals):
                t_stat, p_val = stats.ttest_rel(a_vals, b_vals)
                diff = a_vals - b_vals
                d = np.mean(diff) / np.std(diff, ddof=1) if np.std(diff, ddof=1) > 0 else 0
            else:
                t_stat, p_val = stats.ttest_ind(a_vals, b_vals)
                pooled_sd = np.sqrt(((len(a_vals)-1)*a_std**2 + (len(b_vals)-1)*b_std**2) / (len(a_vals)+len(b_vals)-2))
                d = delta_mean / pooled_sd if pooled_sd > 0 else 0
                
            j_stats[j] = {
                'before_mean': b_mean, 'before_std': b_std, 'before_peak': b_max,
                'after_mean': a_mean, 'after_std': a_std, 'after_peak': a_max,
                'delta_mean': delta_mean, 'delta_peak': delta_max,
                't_stat': t_stat, 'p_val': p_val, 'cohen_d': d,
                'n_before': len(b_vals), 'n_after': len(a_vals)
            }
            
        # Finger sum stats
        f_stats = {}
        for f, j_list in FINGERS.items():
            b_f = pb[j_list].sum(axis=1).values
            a_f = pa[j_list].sum(axis=1).values
            f_stats[f] = {
                'before_mean': np.mean(b_f), 'after_mean': np.mean(a_f),
                'delta': np.mean(a_f) - np.mean(b_f)
            }
            
        # Overall 15 joints mean & sum
        b_all_mean = pb[JOINTS].mean(axis=1).values
        a_all_mean = pa[JOINTS].mean(axis=1).values
        b_all_sum = pb[JOINTS].sum(axis=1).values
        a_all_sum = pa[JOINTS].sum(axis=1).values
        
        overall = {
            'mean_deg': {
                'before_mean': np.mean(b_all_mean), 'before_std': np.std(b_all_mean, ddof=1),
                'after_mean': np.mean(a_all_mean), 'after_std': np.std(a_all_mean, ddof=1),
                'delta': np.mean(a_all_mean) - np.mean(b_all_mean)
            },
            'sum_deg': {
                'before_mean': np.mean(b_all_sum), 'before_std': np.std(b_all_sum, ddof=1),
                'after_mean': np.mean(a_all_sum), 'after_std': np.std(a_all_sum, ddof=1),
                'delta': np.mean(a_all_sum) - np.mean(b_all_sum)
            }
        }
        
        subj_res[hand_label] = {
            'joints': j_stats,
            'fingers': f_stats,
            'overall': overall
        }
        
    # Trial summary metrics (MGA, Duration, Speed, SPARC, TAM)
    tb_aff = data['t_b'][data['t_b']['Hand'] == aff]
    ta_aff = data['t_a'][data['t_a']['Hand'] == aff]
    
    t_metrics = {}
    for col in ['Duration_s', 'TAM_total_deg', 'MGA_cm', 'Flex_Speed_deg_s', 'Ext_Speed_deg_s', 'SPARC', 'Index_ROM_deg', 'Thumb_RadialAbd_max_deg', 'Thumb_PalmarAbd_max_deg']:
        if col in tb_aff.columns and col in ta_aff.columns:
            bv = tb_aff[col].dropna().values
            av = ta_aff[col].dropna().values
            bm, bs = np.mean(bv), np.std(bv, ddof=1) if len(bv)>1 else 0
            am, as_ = np.mean(av), np.std(av, ddof=1) if len(av)>1 else 0
            delta = am - bm
            pct = (delta / bm * 100) if bm != 0 else 0
            if len(bv) == len(av) and len(bv) > 1:
                t_stat, p_val = stats.ttest_rel(av, bv)
                d = np.mean(av - bv) / np.std(av - bv, ddof=1) if np.std(av - bv, ddof=1) > 0 else 0
            elif len(bv) > 1 and len(av) > 1:
                t_stat, p_val = stats.ttest_ind(av, bv)
                pooled_sd = np.sqrt(((len(av)-1)*as_**2 + (len(bv)-1)*bs**2) / (len(av)+len(bv)-2))
                d = delta / pooled_sd if pooled_sd > 0 else 0
            else:
                t_stat, p_val, d = 0, 1, 0
                
            t_metrics[col] = {
                'before_mean': bm, 'before_std': bs,
                'after_mean': am, 'after_std': as_,
                'delta': delta, 'pct_change': pct,
                't_stat': t_stat, 'p_val': p_val, 'cohen_d': d
            }
            
    subj_res['trials_metrics'] = t_metrics
    analysis_output[name] = subj_res

# Save to json for reference
out_json_path = os.path.join(base, 'full_3patients_analysis.json')
with open(out_json_path, 'w', encoding='utf-8') as fp:
    json.dump(analysis_output, fp, ensure_ascii=False, indent=2)

print('Analysis completed and saved to:', out_json_path)
