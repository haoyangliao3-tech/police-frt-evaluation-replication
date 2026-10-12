"""Exploratory complete-case audit and observed-data selection-IPW sensitivity.

This script does not replace or overwrite the primary models. The selection
model uses only variables observed in both retained and excluded respondents.
Its inverse probabilities cannot repair selection on unobserved variables.
"""
from pathlib import Path
import json
import sys

from config import ROOT, SOURCE, OUT
import numpy as np
import pyreadstat
from scipy.optimize import minimize
from scipy.special import expit

from run_actor_pair_checks import fit, ROLES, PUBLIC, POLICE, CONTROLS, OUTCOME


OUTPUT = OUT / "selection_sensitivity.json"
PRIMARY = OUT / "configuration_models.json"
ROLE_LABELS = ["Federal government", "Technology developers", "Ordinary people", "Police departments"]
OUTCOME_LABELS = {1: "Good idea", 2: "Bad idea", 3: "Not sure"}
ROLE_RESPONSE_LABELS = {1: "Major role", 2: "Minor role", 3: "No role"}


def weighted_distribution(frame, variable, labels):
    weight = frame.WEIGHT_W99.to_numpy(float)
    total = weight.sum()
    return [
        {"category": label, "unweighted_n": int(frame[variable].eq(code).sum()),
         "weighted_percent": float(100 * weight[frame[variable].eq(code).to_numpy()].sum() / total)}
        for code, label in labels.items()
    ]


def kish_ess(weight):
    weight = np.asarray(weight, float)
    return float(weight.sum() ** 2 / np.square(weight).sum())


def selection_model(frame):
    """Unweighted logistic inclusion model on wholly observed answers only."""
    model_variables = [OUTCOME, *ROLES]
    assert not frame[model_variables].isna().any().any()
    terms = [(OUTCOME, 1), (OUTCOME, 3)]
    terms += [(role, level) for role in ROLES for level in (1, 3)]
    x = np.column_stack([np.ones(len(frame))] +
                        [frame[column].eq(level).to_numpy(float) for column, level in terms])
    response = frame.retained.to_numpy(float)
    assert np.linalg.matrix_rank(x) == x.shape[1]

    def objective(coef):
        linear = x @ coef
        return float(np.logaddexp(0, linear).sum() - response @ linear)

    def gradient(coef):
        return x.T @ (expit(x @ coef) - response)

    def hessian(coef):
        probability = expit(x @ coef)
        return x.T @ ((probability * (1 - probability))[:, None] * x)

    result = minimize(objective, np.zeros(x.shape[1]), jac=gradient, hess=hessian,
                      method="trust-exact", options={"gtol": 1e-8, "maxiter": 300})
    coef = result.x
    for _ in range(5):
        if np.max(np.abs(gradient(coef))) < 1e-8:
            break
        candidate = coef - np.linalg.solve(hessian(coef), gradient(coef))
        if objective(candidate) > objective(coef) + 1e-9:
            break
        coef = candidate
    probability = expit(x @ coef)
    assert np.all(np.isfinite(probability)) and np.all(probability > 0)
    assert np.max(np.abs(gradient(coef))) < 1e-7
    info = {
        "model": "Unweighted logistic regression of current complete-case retention",
        "predictors": [OUTCOME, *ROLES],
        "reference_categories": {OUTCOME: "Bad idea", **{role: "Minor role" for role in ROLES}},
        "n": int(len(frame)), "retained_n": int(response.sum()),
        "design_rank": int(np.linalg.matrix_rank(x)),
        "design_columns": int(x.shape[1]),
        "max_absolute_gradient": float(np.max(np.abs(gradient(coef)))),
        "optimizer_message": str(result.message),
        "coefficients": coef.tolist(),
        "probability_range_all": [float(probability.min()), float(probability.max())],
        "probability_range_retained": [float(probability[response == 1].min()), float(probability[response == 1].max())],
        "probability_range_excluded": [float(probability[response == 0].min()), float(probability[response == 0].max())],
    }
    return probability, info


def summarize_weights(values):
    q = np.quantile(values, [0, .5, .95, .99, 1])
    return {"min": float(q[0]), "median": float(q[1]), "p95": float(q[2]),
            "p99": float(q[3]), "max": float(q[4]), "kish_effective_n": kish_ess(values)}


def main():
    frame, _ = pyreadstat.read_sav(str(SOURCE))
    frame = frame.loc[frame.FORM_W99.eq(1)].replace(99, np.nan)
    frame = frame.dropna(subset=[OUTCOME, *ROLES]).copy()
    frame["retained"] = frame[CONTROLS].notna().all(axis=1).astype(int)
    retained = frame.loc[frame.retained.eq(1)].copy()
    excluded = frame.loc[frame.retained.eq(0)].copy()
    assert len(frame) == 5080 and len(retained) == 4752 and len(excluded) == 328

    missing_matrix = frame[CONTROLS].isna()
    patterns = {}
    for missing in missing_matrix.itertuples(index=False, name=None):
        names = tuple(column for column, indicator in zip(CONTROLS, missing) if indicator)
        if names:
            patterns[names] = patterns.get(names, 0) + 1
    missing_patterns = [
        {"missing_variables": list(pattern), "n": count,
         "percent_of_excluded": 100 * count / len(excluded)}
        for pattern, count in sorted(patterns.items(), key=lambda item: (-item[1], item[0]))
    ]
    assert sum(p["n"] for p in missing_patterns) == len(excluded)
    missing_by_variable = [
        {"variable": column, "missing_n": int(missing_matrix[column].sum()),
         "missing_percent_of_5080": float(100 * missing_matrix[column].mean()),
         "percent_of_328_exclusions_with_this_missing": float(100 * missing_matrix[column].sum() / len(excluded)),
         "sole_missing_variable_n": int(patterns.get((column,), 0))}
        for column in CONTROLS
    ]
    comparisons = {}
    for column, labels in [(OUTCOME, OUTCOME_LABELS)] + list(zip(ROLES, [ROLE_RESPONSE_LABELS] * 4)):
        comparisons[column] = {
            "name": "Overall deployment evaluation" if column == OUTCOME else ROLE_LABELS[ROLES.index(column)],
            "complete_cases": weighted_distribution(retained, column, labels),
            "excluded_cases": weighted_distribution(excluded, column, labels),
        }

    probability, inclusion_info = selection_model(frame)
    frame["inclusion_probability"] = probability
    retained = frame.loc[frame.retained.eq(1)].copy()
    retained["selection_weight"] = 1 / retained.inclusion_probability
    q01, q99 = np.quantile(retained.selection_weight, [.01, .99])
    retained["selection_weight_trimmed"] = retained.selection_weight.clip(lower=q01, upper=q99)
    retained["combined_untrimmed"] = retained.WEIGHT_W99 * retained.selection_weight
    retained["combined_trimmed"] = retained.WEIGHT_W99 * retained.selection_weight_trimmed
    outcome_balance = {}
    for name, sample, weight in [
        ("all_5080_final_weight", frame, frame.WEIGHT_W99),
        ("complete_original_final_weight", retained, retained.WEIGHT_W99),
        ("complete_selection_ipw_untrimmed", retained, retained.combined_untrimmed),
        ("complete_selection_ipw_trimmed", retained, retained.combined_trimmed),
    ]:
        outcome_balance[name] = {
            OUTCOME_LABELS[code]: float(100 * np.average(sample[OUTCOME].eq(code), weights=weight))
            for code in OUTCOME_LABELS}
    hist_edges = np.histogram_bin_edges(retained.selection_weight, bins=10)
    hist_counts, _ = np.histogram(retained.selection_weight, bins=hist_edges)
    diagnostics = {
        "selection_weight": summarize_weights(retained.selection_weight),
        "selection_weight_trimmed": summarize_weights(retained.selection_weight_trimmed),
        "trimming_rule": "Cap selection weights at the complete-case 1st and 99th percentiles; report both fits regardless of significance",
        "trim_cutoffs": [float(q01), float(q99)],
        "number_below_trim_cutoff": int((retained.selection_weight < q01).sum()),
        "number_above_trim_cutoff": int((retained.selection_weight > q99).sum()),
        "released_final_weight": summarize_weights(retained.WEIGHT_W99),
        "combined_untrimmed_weight": summarize_weights(retained.combined_untrimmed),
        "combined_trimmed_weight": summarize_weights(retained.combined_trimmed),
        "selection_weight_histogram": [
            {"lower": float(hist_edges[i]), "upper": float(hist_edges[i+1]), "n": int(hist_counts[i])}
            for i in range(len(hist_counts))],
    }

    original = fit(retained, (PUBLIC, POLICE), predictions=True, prediction_levels=(1, 2, 3))
    saved = json.loads(PRIMARY.read_text(encoding="utf-8"))["overall_interaction"]
    assert abs(original["wald"] - saved["interaction_test"]["Wald"]) < 1e-5
    for key, configuration in original["configurations"].items():
        p, l = (int(key.split("_")[i]) for i in (1, 3))
        prior = next(row for row in saved["configurations"] if row["public"] == p and row["police"] == l)
        assert np.max(np.abs(np.asarray(configuration["probability"]) - prior["probabilities"])) < 1e-6
    reweighted = fit(retained, (PUBLIC, POLICE), predictions=True,
                     weight_column="combined_untrimmed", prediction_levels=(1, 2, 3))
    trimmed = fit(retained, (PUBLIC, POLICE), predictions=True,
                  weight_column="combined_trimmed", prediction_levels=(1, 2, 3))

    output = {
        "analysis_status": "Exploratory observed-data selection-weighting sensitivity, not a correction proving MAR or eliminating MNAR",
        "sample": {"eligible_form1_n": 5153, "outcome_and_four_roles_valid_n": len(frame),
                   "complete_cases_n": len(retained), "excluded_n": len(excluded)},
        "missing_by_variable": missing_by_variable,
        "missing_patterns": missing_patterns,
        "weighted_answer_comparisons": comparisons,
        "weighted_outcome_balance": outcome_balance,
        "inclusion_model": inclusion_info,
        "weight_diagnostics": diagnostics,
        "outcome_order": ["Good idea", "Not sure", "Bad idea"],
        "models": {"original": original, "selection_ipw_untrimmed": reweighted,
                   "selection_ipw_trimmed_1_99": trimmed},
        "variance_boundary": "HC0 outcome-model covariance conditions on estimated selection weights; it does not propagate uncertainty from the inclusion model or incorporate full complex-survey design information.",
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    for key, model in output["models"].items():
        core = model["contrasts"]["difference_of_differences"]
        print(key, "n", model["n"], "Wald", round(model["wald"], 3), "p", round(model["p_raw"], 6),
              "not_sure_did_pp", round(100 * core["difference"][1], 3),
              "ci_pp", [round(100*x, 3) for x in core["ci95_pointwise"][1]], flush=True)
    print("saved", OUTPUT, flush=True)


if __name__ == "__main__":
    main()

