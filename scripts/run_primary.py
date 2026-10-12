"""Re-run the unchanged primary estimator and original specifications."""
from config import OUT, load, save
from estimator import *
d,_=load()
models={}
def run(name,z,outcome,vs,interaction=True):
    models[name]=fit(z,outcome,vs,interaction)
    print(name,json.dumps({'n':models[name]['n'],'test':models[name].get('interaction_test'),'diagnostics':models[name]['diagnostics']}),flush=True)
    save('configuration_models.json', models)
run('overall_interaction',d,y,roles+controls)
run('overall_additive',d,y,roles+controls,False)
for s in safeguards:
    common=d.dropna(subset=roles+controls+[y,s]);key=s.split('_')[1]
    run(key+'_B_interaction',common,s,roles+controls+[y])
    run(key+'_B_additive',common,s,roles+controls+[y],False)
    run(key+'_A_interaction',common,s,roles+controls)
risk=[f'FACEREC3_{a}_W99' for a in 'abcdef'];common=d.dropna(subset=roles+controls+[y]+risk+['CNCEXC_W99'])
run('overall_risk_common_base',common,y,roles+controls)
run('overall_risk_adjusted',common,y,roles+controls+risk)
run('overall_risk_AI_adjusted',common,y,roles+controls+risk+['CNCEXC_W99'])
core=['overall_interaction']+[a+'_B_interaction' for a in 'abc']
holm([models[k]['interaction_test'] for k in core])
holm([j for k in core for j in models[k]['probability_difference_in_differences']])
for k in core:
    s=y if k=='overall_interaction' else f'FACEREC8_{k[0]}_W99'
    vs=roles+controls+([] if s==y else [y])
    drop=models[k]['diagnostics']['influence_row_index']
    check=fit(d.drop(index=drop),s,vs)
    change=max(abs(np.array(a['probabilities'])-np.array(b['probabilities'])).max() for a,b in zip(models[k]['configurations'],check['configurations']))
    models[k]['targeted_case_deletion_details']=check
    models[k]['targeted_case_deletion_check']={'selection':'Largest first-order influence on any standardized configuration probability; diagnostic only, not a replacement analysis','n':check['n'],'maximum_probability_change':float(change),'interaction_test':check['interaction_test'],'diagnostics':check['diagnostics']}
    print('Influence check',k,float(change),check['interaction_test'],flush=True)
save('configuration_models.json', models)

def proportion(z,indicator):
    w=z.WEIGHT_W99.to_numpy();a=np.asarray(indicator,float);mu=float(np.average(a,weights=w));se=float(np.sqrt(np.sum(w*w*(a-mu)**2))/w.sum())
    return {'n':len(z),'numerator_n':int(a.sum()),'proportion':mu,'se':se,'ci95':interval(mu,se)}
groups=[('All',d)]+[(f'Public {a}',d.loc[d[public].eq(a)]) for a in [1,2,3]]+[(f'Public {a} Police {b}',d.loc[d[public].eq(a)&d[police].eq(b)]) for a,b in itertools.product([1,2,3],repeat=2)]
joint=[]
for name,z in groups:
    for s in safeguards:
        z2=z.dropna(subset=[y,s]);bad=z2.loc[z2[y].eq(2)]
        cells=[]
        for a,b in itertools.product([1,2,3],repeat=2):cells.append({'overall':a,'safeguard':b,**proportion(z2,z2[y].eq(a)&z2[s].eq(b))})
        cc=z2.dropna(subset=roles+controls)
        joint.append({'group':name,'safeguard':s,'joint':proportion(z2,z2[y].eq(2)&z2[s].eq(1)),'conditional':proportion(bad,bad[s].eq(1)),'all_9_cells':cells,'complete_case_joint':proportion(cc,cc[y].eq(2)&cc[s].eq(1))})
(OUT/'joint_estimates_with_intervals.json').write_text(json.dumps(joint,indent=2),encoding='utf-8')
print('COMPLETE',flush=True)

