# Police facial-recognition evaluation: replication materials

This repository provides the analysis code and aggregate outputs for the manuscript *Beyond Acceptance: Separating Public Evaluations of Standard-Setting Roles, Deployment, and Safeguards in Police Facial Recognition* (submitted to *Technology in Society*). It supports a same-estimator rerun of analyses using Pew Research Center’s American Trends Panel (ATP), Wave 99.

## Data access

The Pew Wave 99 respondent-level file is not included. Obtain the SPSS public-use file directly from [Pew Research Center](https://www.pewresearch.org/internet/dataset/american-trends-panel-wave-99/), create/sign in to a Pew account, and follow the applicable access and data-use terms. The original file contains respondent-level survey data and remains subject to Pew’s terms; this repository does not relicense or redistribute it.

Expected input: `ATP W99.sav` (10,260 rows; Form 1 contains 5,153 respondents). The analysis selects Form 1 and applies the released `WEIGHT_W99` weight. The tested release had SHA-256 `cadcfd4a699a163ef3ae7a056c6bd1103cab583b0bf4effaddedd3b9f4ea66ad`; this checksum is provided only to help verify the input file.

## Reproduce the analyses

Tested with Python 3.12.14 and the versions pinned in `requirements.txt`.

```sh
python -m pip install -r requirements.txt
python scripts/run_all.py --data "/absolute/path/ATP W99.sav" --results "./rerun_results"
```

On Windows PowerShell, replace the data argument with the local path to the SAV file. No data path is embedded in the scripts. The workflow runs the primary models, descriptive and conditional estimates, income and selection sensitivities, actor-pair checks, variance-inflation sensitivity, and aggregate table export. It stops if any stage fails. `check_results.py` compares the rerun’s reported model and estimate fields with the included full-precision aggregate reference summaries.

The reported uncertainty estimates use the working variance approach documented in the manuscript; the scripts do not reconstruct unavailable strata, cluster, or replicate-weight information. The repository therefore does not represent a full complex-survey-design variance replication or an independent implementation in another statistical package.

## Repository contents

- `scripts/`: portable analysis, checks, and table-generation scripts.
- `reference_results/`: full-precision aggregate comparison summaries. Case-position diagnostics and snapshots from single-case deletion fits have been removed.
- `results/display_data/`: aggregate CSVs underlying the manuscript’s principal descriptive displays.
- `figures/`: final manuscript PDFs for Figures 1–5 and Figure S1.
- `INPUT_FIELDS.md`: variable coding and sample-selection rules.
- `OUTPUT_MAP.md`: mapping from aggregate files to manuscript outputs.
- `assets/lucide/`: four icons used in artwork, with attribution and third-party licence information.

No respondent-level records, Pew data file, credentials, local workspace paths, or manuscript/title-page source files are included. The scripts may use row positions internally for a diagnostic calculation when run locally; those positions and the case-specific model snapshots are excluded from saved public outputs. The numerical estimates and table values are not altered by this output filter.

## Availability statement

The study uses the public-use American Trends Panel Wave 99 dataset provided by Pew Research Center. The dataset, questionnaire, and survey methodology are available from [Pew Research Center](https://www.pewresearch.org/internet/dataset/american-trends-panel-wave-99/), subject to Pew’s account and data-use terms. Analysis code and aggregate outputs are available in this repository. The underlying respondent-level data are not redistributed.

## Licences

The original analysis code is licensed under the MIT License in `LICENSE`. The aggregate CSV and JSON results and the author-created manuscript figures are licensed under CC BY 4.0 as described in `RESULTS_LICENSE.md`. These licences do not apply to Pew’s respondent-level data or the third-party icons; see `assets/lucide/LICENSE.txt` and `THIRD_PARTY_NOTICES.md` for the icons’ terms.

This GitHub repository does not currently have a DOI. Cite the repository URL and commit/release used; a separately archived version with a persistent identifier can be added later.

