# Results and figure map

The repository contains aggregate outputs only. CSVs in `results/display_data/` are suitable for inspection and reproduce the main descriptive displays. Full-precision model summaries used by `check_results.py` are in `reference_results/`.

| Artifact | Contents / source |
|---|---|
| `main_table1.csv` | Weighted distributions for the three safeguard items |
| `main_table2.csv` | Public/police standard-setting role configurations |
| `main_table3.csv` | Omnibus tests for the focal interaction models |
| `full_joint_grid.csv` | Nine joint deployment–safeguard response cells by group |
| `three_denominators.csv` | Joint, forward-conditional, and reverse-conditional estimates with intervals |
| `favorable_composition.csv` | Deployment evaluations among respondents giving favorable safeguard judgments |
| `observed_configuration_distributions.csv` | Response distributions across public/police role configurations |
| `support_absences.csv` | Aggregate marginal support diagnostics |
| `weight_concentration.csv` | Aggregate weight-concentration diagnostics |
| `figures/Figure_1.pdf`–`Figure_5.pdf` | Final manuscript figures; the PDFs are included for direct inspection |
| `figures/Figure_S1.pdf` | Supplementary measurement map |

The scripts recompute estimates from the Pew SPSS file supplied locally by the user. The figure PDFs are the final manuscript artwork; the concepts and some layout details were manually finalized, so the scripts should not be treated as exact source for every PDF. `reference_results/` is a comparison baseline, not an independent implementation or a substitute for rerunning the code.

Case-position fields and case-deletion model snapshots are omitted from the published aggregate files. The model fits, reported estimates, and table values are unchanged by that omission.
