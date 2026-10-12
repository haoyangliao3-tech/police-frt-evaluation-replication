"""Released-weight distributions, complete joint answers and both conditionals."""
import itertools, hashlib, json
import numpy as np
from config import SOURCE, read_reference, load, save
from estimator import roles, controls, public, police, y, safeguards, proportion

def estimate(frame,indicator):
    r=proportion(frame,indicator)
    w=frame.WEIGHT_W99.to_numpy(float)
    r.update(weighted_denominator=float(w.sum()),weighted_numerator=float(w@np.asarray(indicator,float)))
    return r

def main():
    d,meta=load()
    groups=[('All',d)]+[(f'Public {a}',d.loc[d[public].eq(a)]) for a in [1,2,3]]
    groups += [(f'Public {a} Police {b}',d.loc[d[public].eq(a)&d[police].eq(b)]) for a,b in itertools.product([1,2,3],repeat=2)]
    joint=[]; composition=[]; independence=[]
    for name,z in groups:
        for s in safeguards:
            valid=z.dropna(subset=[y,s]);bad=valid.loc[valid[y].eq(2)];more=valid.loc[valid[s].eq(1)]
            cc=valid.dropna(subset=roles+controls)
            row={'group':name,'safeguard':s,
                'joint':estimate(valid,valid[y].eq(2)&valid[s].eq(1)),
                'conditional':estimate(bad,bad[s].eq(1)),
                'reverse_conditional':estimate(more,more[y].eq(2)),
                'all_9_cells':[{'overall':a,'safeguard':b,**estimate(valid,valid[y].eq(a)&valid[s].eq(b))} for a,b in itertools.product([1,2,3],repeat=2)],
                'complete_case_joint':estimate(cc,cc[y].eq(2)&cc[s].eq(1))}
            assert abs(sum(c['proportion'] for c in row['all_9_cells'])-1)<1e-12
            joint.append(row)
            if name=='All':
                components=[{'code':c,'label':meta.variable_value_labels[y][c],**estimate(more,more[y].eq(c))} for c in [1,2,3]]
                assert abs(sum(c['proportion'] for c in components)-1)<1e-12
                assert sum(c['numerator_n'] for c in components)==len(more)
                composition.append({'safeguard':s,'both_valid_n':len(valid),'favorable_n':len(more),
                    'weighted_favorable_denominator':float(more.WEIGHT_W99.sum()),'deployment_composition':components})
                w=valid.WEIGHT_W99
                b=float(np.average(valid[y].eq(2),weights=w));m=float(np.average(valid[s].eq(1),weights=w))
                independence.append({'safeguard':s,'n':len(valid),'bad':b,'more':m,
                    'observed_joint':row['joint']['proportion'],'product_of_marginals':b*m,'difference':row['joint']['proportion']-b*m})
    reference=read_reference('joint_estimates_with_intervals.json')
    checks=0
    for actual,expected in zip(joint,reference):
        assert (actual['group'],actual['safeguard'])==(expected['group'],expected['safeguard'])
        for key in ['joint','conditional','complete_case_joint']:
            assert actual[key]['n']==expected[key]['n']
            assert actual[key]['numerator_n']==expected[key]['numerator_n']
            assert abs(actual[key]['proportion']-expected[key]['proportion'])<1e-12
            assert abs(actual[key]['se']-expected[key]['se'])<1e-12
            checks+=1
        for a,e in zip(actual['all_9_cells'],expected['all_9_cells']):
            assert abs(a['proportion']-e['proportion'])<1e-12
            checks+=1
    frequencies={}
    for v in [y,*roles,*safeguards]:
        frequencies[v]={'valid_n':int(d[v].notna().sum()),'eligible_n':len(d),
            'eligible_denominator':[{'code':c,**estimate(d,d[v].eq(c))} for c in [1,2,3]],
            'valid_denominator':[{'code':c,**estimate(d.dropna(subset=[v]),d.dropna(subset=[v])[v].eq(c))} for c in [1,2,3]]}
    rolebase=d.dropna(subset=[public,police]);cc=d.dropna(subset=[y,*roles,*controls])
    configurations=[{'public':a,'police':b,'valid_n':int((rolebase[public].eq(a)&rolebase[police].eq(b)).sum()),
        'weighted_share':estimate(rolebase,rolebase[public].eq(a)&rolebase[police].eq(b))['proportion'],
        'complete_case_n':int((cc[public].eq(a)&cc[police].eq(b)).sum())} for a,b in itertools.product([1,2,3],repeat=2)]
    observed=[]; major_bad=[]
    for target in [y,*safeguards]:
        for a,b in itertools.product([1,2,3],repeat=2):
            z=d.loc[d[public].eq(a)&d[police].eq(b)].dropna(subset=[target])
            observed.append({'variable':target,'public':a,'police':b,'valid_n':len(z),
                'responses':[{'code':c,**estimate(z,z[target].eq(c))} for c in [1,2,3]]})
    for target in safeguards:
        z=d.loc[d[public].eq(1)&d[y].eq(2)].dropna(subset=[target])
        major_bad.append({'safeguard':target,**estimate(z,z[target].eq(1))})
    for r,n,nmore,pct in zip(major_bad,[796,797,797],[394,387,418],[54.3,50.0,50.0]):
        assert r['n']==n and r['numerator_n']==nmore and round(100*r['proportion'],1)==pct
    fields=['FORM_W99','WEIGHT_W99',y,*roles,*controls,*safeguards,
            *[f'FACEREC3_{a}_W99' for a in 'abcdef'],'CNCEXC_W99']
    save('input_value_labels.json',{'source':'SPSS release metadata',
        'fields':{v:{'label':meta.column_names_to_labels[v],
                     'value_labels':meta.variable_value_labels.get(v,{})} for v in fields}})
    save('joint_estimates_with_intervals.json',joint)
    save('favorable_deployment_composition.json',{'raw_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'weight':'WEIGHT_W99','denominator':'More acceptable, with both deployment and safeguard responses valid',
        'variance':'Individual ratio-mean working linearization and pointwise logit intervals','items':composition})
    save('descriptive_audit.json',{'raw_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'eligible_n':len(d),'saved_estimate_objects_checked':checks,'frequencies':frequencies,
        'role_configurations':configurations,'independence_descriptive_reference':independence,
        'observed_configuration_distributions':observed,'public_major_bad_safeguard':major_bad,
        'value_labels':{v:meta.variable_value_labels.get(v,{}) for v in [y,*roles,*controls,*safeguards]}})
    print('Descriptive reference checks passed',checks,flush=True)
    for item in composition:
        print(item['safeguard'],item['favorable_n'],[(c['label'],round(100*c['proportion'],5)) for c in item['deployment_composition']],flush=True)

if __name__=='__main__': main()
