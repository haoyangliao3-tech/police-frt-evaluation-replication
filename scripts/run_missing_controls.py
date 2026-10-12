"""Reproduce pre-existing additive missing-control and conditional descriptions."""
import numpy as np
from config import load,save
from additive_estimator import fit,roles,controls,y
d,_=load();out={};z=d.copy()
for v in controls:z[v]=z[v].fillna(999)
for name,frame,vs in [('missing_control_categories',z,roles+controls),
                     ('omit_income',d,roles+[v for v in controls if v!='F_INC_TIER2'])]:
    out[name]=fit(frame,vs)
def proportion(frame,v,level):
    zz=frame.dropna(subset=[v]);w=zz.WEIGHT_W99.to_numpy();a=zz[v].eq(level).to_numpy().astype(float)
    p=float(np.average(a,weights=w));se=float(np.sqrt(np.sum((w*(a-p))**2))/w.sum())
    return {'n':len(zz),'pct':100*p,'low':100*max(0,p-1.96*se),'high':100*min(1,p+1.96*se)}
out['safeguards']=[]
for v in [f'FACEREC8_{a}_W99' for a in 'abc']:
    for group,frame in [('all',d),('good',d.loc[d[y].eq(1)]),('bad',d.loc[d[y].eq(2)]),('unsure',d.loc[d[y].eq(3)])]:
        out['safeguards'].append({'variable':v,'group':group,'responses':{str(c):proportion(frame,v,c) for c in [1,2,3]},'missing_n':int(frame[v].isna().sum())})
save('missing_safeguards.json',out)
