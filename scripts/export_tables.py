"""Export manuscript-facing aggregate CSVs from freshly generated JSON outputs."""
import csv, json
from config import OUT, save

DEST = OUT / 'display_data'
DEST.mkdir(exist_ok=True)

def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

def write(name, rows):
    if not rows:
        raise ValueError(f'No rows to export for {name}')
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (DEST / name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

d = read('descriptive_audit.json')
m = read('configuration_models.json')
write('main_table1.csv', [
    {'safeguard': v, 'n': d['frequencies'][v]['valid_n'],
     **{str(r['code']) + '_pct': 100*r['proportion']
        for r in d['frequencies'][v]['valid_denominator']}}
    for v in ['FACEREC8_a_W99', 'FACEREC8_b_W99', 'FACEREC8_c_W99']])
write('main_table2.csv', [
    {**r, 'weighted_share_pct': 100*r['weighted_share']}
    for r in d['role_configurations']])
write('main_table3.csv', [
    {'model': k, 'n': m[k]['n'], **m[k]['interaction_test']}
    for k in ['overall_interaction', 'a_B_interaction', 'b_B_interaction', 'c_B_interaction']])

joint = read('joint_estimates_with_intervals.json')
composition = read('favorable_deployment_composition.json')
write('full_joint_grid.csv', [
    {'group': r['group'], 'safeguard': r['safeguard'], **cell}
    for r in joint for cell in r['all_9_cells']])
write('three_denominators.csv', [
    {'group': r['group'], 'safeguard': r['safeguard'], 'estimand': key,
     **{k: v for k, v in r[key].items() if k != 'ci95'},
     'low': r[key]['ci95'][0], 'high': r[key]['ci95'][1]}
    for r in joint for key in ['joint', 'conditional', 'reverse_conditional']])
write('favorable_composition.csv', [
    {'safeguard': r['safeguard'], 'both_valid_n': r['both_valid_n'],
     'favorable_n': r['favorable_n'], **{k: v for k, v in c.items() if k != 'ci95'},
     'low': c['ci95'][0], 'high': c['ci95'][1]}
    for r in composition['items'] for c in r['deployment_composition']])
write('observed_configuration_distributions.csv', [
    {'variable': r['variable'], 'public': r['public'], 'police': r['police'], **c}
    for r in d['observed_configuration_distributions'] for c in r['responses']])
write('S5_public_major_bad.csv', d['public_major_bad_safeguard'])

support = read('support_influence_diagnostics.json')['models']
write('support_absences.csv', [
    {'model': name, 'public': r['public'], 'police': r['police'],
     'configuration_n': r['observed_n'], **a}
    for name, model in support.items() for r in model['support']
    for a in r['absent_categories']])
write('weight_concentration.csv', [
    {'model': name, **{k: v for k, v in r.items()
                       if k not in ['absent_categories', 'probabilities']}}
    for name, model in support.items() for r in model['support']])
save('display_export_audit.json', {
    'dynamic_source': 'Fresh aggregate outputs generated from the SAV input',
    'dynamic_files': sorted(p.name for p in DEST.glob('*.csv')),
    'case-position diagnostics omitted': True,
    'manuscript/SI presentation templates included': False})
print('Aggregate display CSVs exported:', len(list(DEST.glob('*.csv'))), flush=True)
