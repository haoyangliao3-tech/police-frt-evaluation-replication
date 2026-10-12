"""Portable orchestration with per-stage stdout, stderr and exit-code records."""
from pathlib import Path
import argparse, subprocess, sys, os, json, hashlib, datetime, importlib.metadata
parser=argparse.ArgumentParser()
parser.add_argument('--data',required=True,type=Path)
parser.add_argument('--results',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
out=(args.results or root/'results').resolve();out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env['W99_DATA']=str(args.data.resolve());env['W99_OUTPUT']=str(out)
env['OPENBLAS_NUM_THREADS']='1';env['OMP_NUM_THREADS']='1';env['PYTHONIOENCODING']='utf-8'
record={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'data_sha256':hashlib.sha256(args.data.read_bytes()).hexdigest(),'data_redistributed':False,
    'python':sys.version,'packages':{p:importlib.metadata.version(p) for p in ['numpy','scipy','pandas','pyreadstat']},
    'stages':[],'method':'Author-code rerun, not independent implementation'}
stages=['run_primary.py','run_descriptives.py','run_income.py','run_actor_pair_checks.py',
        'run_selection_sensitivity.py','variance_inflation_sensitivity.py','run_additive.py','run_missing_controls.py',
        'diagnose_support_influence.py','check_results.py','export_tables.py']
for script in stages:
    print('START',script,flush=True)
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    run=subprocess.run([sys.executable,str(root/'scripts'/script)],env=env,cwd=root,capture_output=True,text=True,encoding='utf-8')
    (out/(script+'.stdout.log')).write_text(run.stdout,encoding='utf-8')
    (out/(script+'.stderr.log')).write_text(run.stderr,encoding='utf-8')
    record['stages'].append({'script':script,'started_utc':start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':run.returncode})
    record['status']='RUNNING' if run.returncode==0 else 'FAILED'
    (out/'execution_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    if run.returncode:
        print(run.stderr,flush=True);raise SystemExit(run.returncode)
    print('PASS',script,flush=True)
record['status']='PASS';record['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
assert hashlib.sha256(args.data.read_bytes()).hexdigest()==record['data_sha256']
(out/'execution_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')

