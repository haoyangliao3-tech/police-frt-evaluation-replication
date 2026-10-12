"""Hypothetical scalar inflation of saved working covariance, without refitting.

The saved full-precision Wald statistics and difference-of-differences estimates
come from run_configuration_models.py. The focal SE is recovered from its saved
unrounded pointwise 95% interval, which that script formed as estimate +/- 1.96 SE.
"""

from pathlib import Path
import json
import sys

from config import ROOT, OUT
from scipy.stats import chi2, norm

SOURCE = OUT / "configuration_models.json"
OUTPUT = OUT / "variance_inflation_sensitivity.json"
KEYS = ["overall_interaction", "a_B_interaction", "b_B_interaction", "c_B_interaction"]
LABELS = ["Deployment", "Opt-out B", "Notification B", "Training B"]
MULTIPLIERS = [1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.50]


def holm(p_values):
    adjusted = [None] * len(p_values)
    running = 0.0
    for rank, index in enumerate(sorted(range(len(p_values)), key=p_values.__getitem__)):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def main():
    saved = json.loads(SOURCE.read_text(encoding="utf-8"))
    tests = [saved[key]["interaction_test"] for key in KEYS]
    contrasts = [item for key in KEYS for item in saved[key]["probability_difference_in_differences"]]
    assert len(contrasts) == 24
    focal = next(item for item in saved[KEYS[0]]["probability_difference_in_differences"]
                 if item["police_level"] == 1 and item["police_reference"] == 2
                 and item["outcome_code"] == 3)

    def contrast_se(item):
        low, high = item["ci95"]
        estimate = item["difference"]
        assert abs((low + high) / 2 - estimate) < 1e-10
        return (high - low) / (2 * 1.96)

    # The 1.00 row must reproduce the saved results before any sensitivity
    # numbers are accepted. This checks both Holm families, not just the focal p.
    primary_base = [chi2.sf(test["Wald"], test["df"]) for test in tests]
    contrast_base = [2 * norm.sf(abs(item["difference"] / contrast_se(item))) for item in contrasts]
    for actual, test in zip(primary_base, tests):
        assert abs(actual - test["p"]) < 1e-10
    for actual, item in zip(contrast_base, contrasts):
        assert abs(actual - item["p"]) < 1e-10
    for actual, test in zip(holm(primary_base), tests):
        assert abs(actual - test["p_Holm"]) < 1e-10
    for actual, item in zip(holm(contrast_base), contrasts):
        assert abs(actual - item["p_Holm"]) < 1e-10

    focal_index = next(i for i, item in enumerate(contrasts) if item is focal)
    focal_se = contrast_se(focal)
    rows = []
    for multiplier in MULTIPLIERS:
        primary_p = [chi2.sf(test["Wald"] / multiplier**2, test["df"]) for test in tests]
        primary_holm = holm(primary_p)
        contrast_p = [2 * norm.sf(abs(item["difference"] / (multiplier * contrast_se(item))))
                      for item in contrasts]
        contrast_holm = holm(contrast_p)
        rows.append({
            "se_multiplier": multiplier,
            "covariance_multiplier": multiplier**2,
            "primary_tests": [
                {"label": label, "wald": test["Wald"] / multiplier**2,
                 "raw_p": primary_p[i], "holm_p": primary_holm[i]}
                for i, (label, test) in enumerate(zip(LABELS, tests))
            ],
            "focal_not_sure_did": {
                "estimate_pp": focal["difference"] * 100,
                "se_pp": focal_se * multiplier * 100,
                "ci95_pp": [(focal["difference"] + sign * 1.96 * focal_se * multiplier) * 100
                            for sign in (-1, 1)],
                "raw_p": contrast_p[focal_index],
                "holm_p": contrast_holm[focal_index],
            },
        })
    OUTPUT.write_text(json.dumps({"source": str(SOURCE.relative_to(ROOT)), "rows": rows}, indent=2),
                      encoding="utf-8")
    print("Base-row validation passed for 4 omnibus tests and 24 contrasts.")
    print("SE m | Deployment Wald | raw p | Holm p | Focal CI pp | focal raw p | focal Holm p")
    for row in rows:
        test = row["primary_tests"][0]
        contrast = row["focal_not_sure_did"]
        low, high = contrast["ci95_pp"]
        print(f"{row['se_multiplier']:.2f} | {test['wald']:.2f} | {test['raw_p']:.5f} | "
              f"{test['holm_p']:.5f} | [{low:.2f}, {high:.2f}] | "
              f"{contrast['raw_p']:.5f} | {contrast['holm_p']:.5f}")


if __name__ == "__main__":
    main()

