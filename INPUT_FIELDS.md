# Input fields and coding conventions

The public release has 10,260 respondents. FORM_W99 = 1 selects the 5,153 eligible police-FRT respondents. Form 2 structural skips are not coded as responses. WEIGHT_W99 must be finite and positive. It is rescaled to mean one within a model sample, preserving relative released weights.

| Field | Use / original codes |
|---|---|
| FORM_W99 | 1 = police FRT form; filter before analysis |
| WEIGHT_W99 | released final respondent weight |
| FACEREC2_W99 | deployment: 1 Good idea for society; 2 Bad idea for society; 3 Not sure; 99 Refused |
| FACEREC6_a_W99 | federal government standard-setting role |
| FACEREC6_b_W99 | technology developer role |
| FACEREC6_c_W99 | ordinary people role |
| FACEREC6_d_W99 | police department role |
| all four role fields | 1 A major role; 2 A minor role; 3 No role at all; 99 Refused |
| FACEREC8_a_W99 | database opt-out for people without criminal records |
| FACEREC8_b_W99 | notification of scanned public events and spaces |
| FACEREC8_c_W99 | officer training about identification errors before use |
| all three safeguard fields | 1 More acceptable; 2 Less acceptable; 3 No difference; 99 Refused |
| F_AGECAT | 1 18–29; 2 30–49; 3 50–64; 4 65+ |
| F_GENDER | 1 A man; 2 A woman; 3 In some other way |
| F_EDUCCAT | 1 College graduate+; 2 Some College; 3 H.S. graduate or less |
| F_RACETHNMOD | 1 White non-Hispanic; 2 Black non-Hispanic; 3 Hispanic; 4 Other; 5 Asian non-Hispanic |
| F_PARTYSUM_FINAL | 1 Rep/Lean Rep; 2 Dem/Lean Dem; 9 DK/Refused/No lean |
| F_INC_TIER2 | 1 Lower income; 2 Middle income; 3 Upper income |
| F_METRO | 1 Metropolitan; 2 Non-metropolitan |
| FACEREC1_W99 | FRT familiarity: 1 A lot; 2 A little; 3 Nothing at all |
| FACEREC3_a_W99 … FACEREC3_f_W99 | six separate categorical consequence judgments; no summed risk scale |
| CNCEXC_W99 | separate categorical general-AI attitude sensitivity |

Released code 99 is missing; system missing values remain missing. Party code 9 is an actual released combined category retained in the primary models, not automatically treated as missing. Its omission is an existing sensitivity. results/input_value_labels.json is extracted from SAV metadata and records all these fields' exact category labels, including the separate consequence and AI codes.

## Denominators and references

- Eligible descriptions retain refusals in the 5,153 denominator where stated (S1).
- Main Table 1 uses valid responses for that safeguard alone.
- Joint grid: valid on deployment and that safeguard.
- Forward: bad-idea deployment respondents valid on that safeguard.
- Reverse / favorable composition: more-acceptable safeguard respondents valid on deployment. Good, bad, and not sure share exactly this denominator.
- Regression: complete cases for the particular model's fields, not a common universal denominator; safeguard A/B samples are held equal.
- Role predictor reference = minor role; other categorical predictor reference = minimum observed code in the fitted sample. Missing-income category exists only in its defined sensitivity.
- Interaction estimator outcome order: deployment [1,3,2] (Bad as baseline), safeguard [1,2,3] (No difference as baseline). The older additive helper internally maps safeguards to its own [1,3,2] coding; exported contrasts are relabeled to the original More/Less/No difference categories. The raw data are never recoded in place.

The questionnaire's FRT description precedes deployment, role and safeguard questions. The three technology blocks and items within role/safeguard batteries were randomized; the relative sequence within the FRT block was not all-randomized. No repeated deployment evaluation under an identical implemented safeguard was collected.

No identifiable sampling-stratum, PSU/cluster or replicate-weight field was found in the inspected public file. Final weights alone do not reconstruct the full sampling-design covariance.

