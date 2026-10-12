"""Compare new executable outputs to archived full-precision estimates."""
import json, math
from config import OUT, read_reference, save
checks=[]
excluded_fields=[]
def compare(a,b,path,atol=1e-5):
    if isinstance(b,dict):
        for k,v in b.items():
            if k in ['optimizer_message','message','BFGS_success','optimizer_success','gradient_check_at_zero','protected_hashes','source','original_source_hashes_unchanged','selection','influence_row_index','targeted_case_deletion_details','deletion']:
                excluded_fields.append(path+'/'+k)
                continue
            assert k in a, ('Missing reference field', path+'/'+k)
            compare(a[k],v,path+'/'+k,atol)
    elif isinstance(b,list):
        assert len(a)==len(b),(path,len(a),len(b))
        for i,(u,v) in enumerate(zip(a,b)):compare(u,v,path+'/'+str(i),atol)
    elif isinstance(b,(float,int)) and not isinstance(b,bool):
        assert math.isfinite(float(a)) and abs(a-b)<=atol,(path,a,b)
        checks.append({'path':path,'absolute_error':abs(a-b),'tolerance':atol})
    elif b is None: assert a is None,path
    elif isinstance(b,str) and path.endswith(('/group','/safeguard')):assert a==b,path
for name in ['configuration_models.json','actor_pair_checks.json','selection_sensitivity.json',
             'variance_inflation_sensitivity.json','model_results.json','safeguards_models.json','risk_sensitivity.json','missing_safeguards.json']:
    actual=json.loads((OUT/name).read_text())
    expected=read_reference(name)
    compare(actual,expected,name)
compare(json.loads((OUT/'joint_estimates_with_intervals.json').read_text()),
        read_reference('joint_estimates_with_intervals.json'),'joint',1e-12)
income=json.loads((OUT/'income_sensitivity.json').read_text())
prior=read_reference('income_sensitivity.json')
compare(income['models'],prior['models'],'income')
save('reproduction_comparison.json',{'status':'PASS','comparison_kind':'Same estimator rerun from raw data in portable code; not independent software validation',
    'scalar_values_checked':len(checks),'maximum_absolute_error':max(c['absolute_error'] for c in checks),
    'model_tolerance':1e-5,'descriptive_tolerance':1e-12,
    'excluded_fields':excluded_fields,
    'exclusion_reason':'Optimizer status strings and source/provenance metadata may differ by environment. selection is an archived non-manuscript diagnostic in risk_sensitivity; the manuscript observed-selection models are separately rerun and compared in selection_sensitivity.json. All other expected fields must exist.',
    'checks':checks})
print('PASS',len(checks),'scalar values; maximum absolute error',max(c['absolute_error'] for c in checks),flush=True)

