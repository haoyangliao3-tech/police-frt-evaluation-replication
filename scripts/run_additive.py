"""Original additive actor contrasts and specifications, without auxiliary datasets."""
import numpy as np
import additive_estimator as ae
from config import load, save
d,_=load();roles=ae.roles;controls=ae.controls;y=ae.y
common=d.dropna(subset=[y]+roles+controls+['CNCEXC_W99'])
results={}
for name,z,vs,w in [('M0',d,roles,True),('M1',d,roles+controls,True),
    ('M2',d,roles+controls+['CNCEXC_W99'],True),('M0_common',common,roles,True),
    ('M1_common',common,roles+controls,True),('M1_unweighted',d,roles+controls,False),
    ('M1_no_party9',d.loc[d.F_PARTYSUM_FINAL.ne(9)],roles+controls,True)]:
    results[name]=ae.fit(z,vs,w);print(name,results[name]['n'],flush=True)
save('model_results.json',results)
safe={}
for letter in 'abc':
    target=f'FACEREC8_{letter}_W99';frame=d.copy()
    frame['SAFE_OUTCOME']=frame[target].map({1:1,2:3,3:2});ae.y='SAFE_OUTCOME'
    frame=frame.dropna(subset=['SAFE_OUTCOME']+roles+controls+[y])
    for model,vs in [('demographics',roles+controls),('plus_evaluation',roles+controls+[y])]:
        r=ae.fit(frame,vs)
        for c in r['contrasts']:c['order']=['more_acceptable','less_acceptable','no_difference']
        safe[f'{letter}_{model}']=r
for model in ['demographics','plus_evaluation']:
    ts=[t for a in 'abc' for t in safe[f'{a}_{model}']['tests']];prev=0
    for rank,i in enumerate(np.argsort([t['p'] for t in ts])):
        prev=max(prev,min(1,(12-rank)*ts[i]['p']));ts[i]['p_Holm_12']=prev
save('safeguards_models.json',safe)
ae.y=y
risk=[f'FACEREC3_{a}_W99' for a in 'abcdef']
common=d.dropna(subset=[y]+roles+controls+risk+['CNCEXC_W99'])
risk_results={}
for name,vs in [('M1_common_risk',roles+controls),('M3_risk_benefit',roles+controls+risk),
                ('M4_risk_benefit_AI',roles+controls+risk+['CNCEXC_W99'])]:
    risk_results[name]=ae.fit(common,vs);print(name,risk_results[name]['n'],flush=True)
save('risk_sensitivity.json',risk_results)

