"""Exact support summaries and the previously specified one-case deletion.

Selection is the saved largest first-order influence on any configuration
probability. The full-sample model is unchanged. Deletion predictions use the
deleted sample's distribution, exactly as in the original diagnostic.
"""
import hashlib, json
from pathlib import Path
import numpy as np
from config import SOURCE, OUT, load, save
from estimator import fit, roles, controls, public, police, y, safeguards

def focal(result):
    return next(c for c in result['probability_difference_in_differences']
                if c['police_level']==1 and c['police_reference']==2 and c['outcome_code']==3)

def main():
    raw_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    d,meta=load()
    saved=json.loads((OUT/'configuration_models.json').read_text())
    output={'raw_sha256':raw_hash,'selection_rule':'Previously saved largest first-order influence on any of 27 standardized configuration probabilities',
            'standardization':'Each fit uses its own retained weighted covariate distribution; deletion changes both fit and distribution',
            'support_metric':'Marginal covariate-category support within an observed role configuration; not full joint positivity',
            'models':{},'value_labels':{}}
    for key,target in [('overall_interaction',y),*[(a+'_B_interaction',s) for a,s in zip('abc',safeguards)]]:
        vs=roles+controls+([] if target==y else [y])
        z=d.dropna(subset=[target]+vs)
        published=saved[key]
        # Refit in memory to recover the diagnostic case position locally. The
        # saved comparison output deliberately omits that position.
        original=fit(z,target,vs)
        assert len(z)==original['n']==published['n']
        profiles=[]
        for row in original['configurations']:
            a,b=row['public'],row['police']
            observed=z.loc[z[public].eq(a)&z[police].eq(b)]
            w=observed.WEIGHT_W99.to_numpy(float)
            support=[]
            for var in vs:
                if var in [public,police]: continue
                absent=sorted(set(z[var].unique())-set(observed[var].unique()))
                for level in absent:
                    mask=z[var].eq(level)
                    support.append({'variable':var,'code':float(level),'label':meta.variable_value_labels[var].get(level,'Unlabelled'),
                                    'configuration_category_n':0,'model_category_n':int(mask.sum()),
                                    'model_category_weighted_share':float(z.loc[mask,'WEIGHT_W99'].sum()/z.WEIGHT_W99.sum())})
                output['value_labels'][var]=meta.variable_value_labels.get(var,{})
            actual={v:sorted({c['code'] for c in support if c['variable']==v}) for v in {c['variable'] for c in support}}
            recorded={r['variable']:r['absent_levels'] for r in row['absent_covariate_levels']}
            assert actual==recorded,(key,a,b,actual,recorded)
            profiles.append({'public':a,'police':b,'observed_n':len(observed),
                'weighted_share_of_model':float(w.sum()/z.WEIGHT_W99.sum()),
                'kish_effective_n':float(w.sum()**2/(w@w)),
                'largest_weight_share_within_configuration':float(w.max()/w.sum()),
                'top_5_weight_share_within_configuration':float(np.sort(w)[-5:].sum()/w.sum()),
                'max_to_median_weight':float(w.max()/np.median(w)),
                'absent_categories':support,'probabilities':row['probabilities']})
        drop=original['diagnostics']['influence_row_index']
        assert drop in z.index
        deleted=fit(d.drop(index=drop),target,vs)
        before=np.array([c['probabilities'] for c in original['configurations']])
        after=np.array([c['probabilities'] for c in deleted['configurations']])
        idx=np.unravel_index(np.argmax(np.abs(after-before)),before.shape)
        profile=original['configurations'][idx[0]]
        actualmax=float(np.max(np.abs(after-before)))
        assert abs(actualmax-published['targeted_case_deletion_check']['maximum_probability_change'])<1e-7
        detail={'deleted_row_position_zero_based':int(drop),'n_before':len(z),'n_after':deleted['n'],
                'most_affected_public':profile['public'],'most_affected_police':profile['police'],
                'most_affected_outcome_code':original['order'][idx[1]],
                'probability_before':float(before[idx]),'probability_after':float(after[idx]),
                'signed_change_pp':float(100*(after-before)[idx]),'maximum_absolute_change_pp':100*actualmax,
                'all_before':original['configurations'],'all_after':deleted['configurations'],
                'interaction_before':original['interaction_test'],'interaction_after':deleted['interaction_test'],
                'diagnostics_before':original['diagnostics'],'diagnostics_after':deleted['diagnostics']}
        if target==y:
            f0,f1=focal(original),focal(deleted)
            detail['focal_not_sure']={'before_pp':100*f0['difference'],'after_pp':100*f1['difference'],
                'signed_change_pp':100*(f1['difference']-f0['difference']),
                'before_pointwise_ci_pp':[100*c for c in f0['ci95']],
                'after_pointwise_ci_pp':[100*c for c in f1['ci95']],
                'inference':'Diagnostic contrast only; no new Holm family or confirmatory decision',
                'components_before':original['public_major_minus_minor'],
                'components_after':deleted['public_major_minus_minor']}
        output['models'][key]={'n':len(z),'support':profiles,'deletion':detail}
        save('support_influence_diagnostics.json',output)
        print(key,json.dumps({k:v for k,v in detail.items() if k not in ['all_before','all_after','diagnostics_before','diagnostics_after']},ensure_ascii=False),flush=True)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==raw_hash

if __name__=='__main__': main()
