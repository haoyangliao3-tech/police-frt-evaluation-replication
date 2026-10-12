"""Three original income branches, four models and separate Holm families."""
import re, numpy as np
from config import load, save
from estimator import fit, holm, roles, controls, y, safeguards
d,meta=load()
base=d.dropna(subset=[y,*roles]);kept=base.dropna(subset=controls)
excluded=base.loc[~base.index.isin(kept.index)]
other=[c for c in controls if c!='F_INC_TIER2']
recovered=base.dropna(subset=other).loc[lambda z:z.F_INC_TIER2.isna()]
report={'design_field_search':[(n,l) for n,l in zip(meta.column_names,meta.column_labels) if re.search(r'weight|strat|cluster|psu|replic',n+' '+str(l),re.I)],
    'public_use_columns':len(meta.column_names),'eligible_n':len(d),
    'deployment_and_roles_valid_n':len(base),'complete_n':len(kept),'excluded_n':len(excluded),
    'excluded_income_tier_missing_n':int(excluded.F_INC_TIER2.isna().sum()),
    'income_only_missing_n':len(recovered),
    'income_tier_missing_but_raw_income_valid_n':int((base.F_INC_TIER2.isna()&base.F_INC_SDT1.notna()).sum()),'models':{}}
for branch in ['omit_income_common','omit_income_expanded','missing_income_category']:
    results={}
    for key,outcome in [('overall_interaction',y),*[(a+'_B_interaction',s) for a,s in zip('abc',safeguards)]]:
        needed=[*roles,*controls,y]+([] if outcome==y else [outcome])
        z=d.dropna(subset=needed) if branch=='omit_income_common' else d.dropna(subset=[v for v in needed if v!='F_INC_TIER2'])
        vs=roles+other+([] if outcome==y else [y])
        if branch=='missing_income_category':
            z=z.copy();z['F_INC_TIER2']=z['F_INC_TIER2'].fillna(4)
            vs=roles+controls+([] if outcome==y else [y])
        results[key]=fit(z,outcome,vs)
        print(branch,key,results[key]['n'],flush=True)
    holm([r['interaction_test'] for r in results.values()])
    holm([c for r in results.values() for c in r['probability_difference_in_differences']])
    report['models'][branch]=results
    save('income_sensitivity.json',report)

