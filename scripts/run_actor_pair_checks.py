"""Exploratory six-pair benchmark and major/minor-only sensitivity.

Uses the same released cases, final weights, covariates, outcome coding,
and individual-score HC0 sandwich as run_configuration_models.py.
Does not overwrite primary model results.
"""
from pathlib import Path
import itertools
import json
import sys

from config import ROOT, SOURCE, OUT, load
import numpy as np
import pyreadstat
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from scipy.stats import chi2, norm

ROLES = [f"FACEREC6_{a}_W99" for a in "abcd"]
GOVERNMENT, DEVELOPER, PUBLIC, POLICE = ROLES
CONTROLS = ["F_AGECAT", "F_GENDER", "F_EDUCCAT", "F_RACETHNMOD",
            "F_PARTYSUM_FINAL", "F_INC_TIER2", "F_METRO", "FACEREC1_W99"]
OUTCOME = "FACEREC2_W99"
OUTCOME_ORDER = [1, 3, 2]  # good, not sure, bad (reference)

DEST = OUT / "actor_pair_checks.json"


def fit(frame, pair, predictions=False, weight_column="WEIGHT_W99", prediction_levels=(1, 2)):
    needed = [OUTCOME, *ROLES, *CONTROLS]
    frame = frame.dropna(subset=needed).copy()
    n = len(frame)
    w = frame[weight_column].to_numpy(float).copy()
    w /= w.mean()
    variables = ROLES + CONTROLS
    terms = [(v, c) for v in variables
             for c in sorted(frame[v].unique())
             if c != (2 if v in ROLES else min(frame[v].unique()))]
    levels = [sorted(set(frame[v].unique()) - {2}) for v in pair]
    products = list(itertools.product(*levels))

    def design(data):
        cols = [np.ones(len(data))]
        cols += [data[v].eq(c).to_numpy(float) for v, c in terms]
        cols += [(data[pair[0]].eq(a) & data[pair[1]].eq(b)).to_numpy(float)
                 for a, b in products]
        return np.column_stack(cols)

    x = design(frame)
    n, p = x.shape
    assert np.linalg.matrix_rank(x) == p, "Design not full rank"
    yy = np.column_stack([frame[OUTCOME].eq(c).to_numpy(float)
                          for c in OUTCOME_ORDER[:2]])

    def probabilities(beta, design_matrix=x):
        eta = design_matrix @ beta.reshape(2, p).T
        return softmax(np.column_stack([eta, np.zeros(len(eta))]), axis=1)

    def objective(beta):
        eta = x @ beta.reshape(2, p).T
        return np.sum(w * (logsumexp(np.column_stack([eta, np.zeros(n)]), axis=1)
                           - (yy * eta).sum(axis=1)))

    def gradient(beta):
        return ((w[:, None] * (probabilities(beta)[:, :2] - yy)).T @ x).ravel()

    def hessian(beta):
        pr = probabilities(beta)
        return np.block([[x.T @ ((w * pr[:, j] * ((j == k) - pr[:, k]))[:, None] * x)
                          for k in range(2)] for j in range(2)])

    result = minimize(objective, np.zeros(2*p), jac=gradient, hess=hessian,
                      method="trust-exact", options={"gtol": 1e-7, "maxiter": 300})
    beta = result.x
    for _ in range(8):
        if np.max(np.abs(gradient(beta))) < 1e-7:
            break
        proposed = beta - np.linalg.solve(hessian(beta), gradient(beta))
        if objective(proposed) > objective(beta) + 1e-8:
            break
        beta = proposed
    h = hessian(beta)
    inv_h = np.linalg.inv(h)
    score = (w[:, None, None] * (yy - probabilities(beta)[:, :2])[:, :, None]
             * x[:, None, :]).reshape(n, -1)
    covariance = inv_h @ (score.T @ score) @ inv_h
    covariance = (covariance + covariance.T) / 2
    ids = list(range(p - len(products), p)) + list(range(2*p - len(products), 2*p))
    statistic = float(beta[ids] @ np.linalg.solve(covariance[np.ix_(ids, ids)], beta[ids]))
    df = len(ids)
    out = {
        "n": n, "pair": list(pair), "interaction_terms_per_equation": len(products),
        "design_columns_per_equation": p, "design_rank": int(np.linalg.matrix_rank(x)),
        "gradient_max": float(np.max(np.abs(gradient(beta)))),
        "hessian_min_eigenvalue": float(np.linalg.eigvalsh(h).min()),
        "wald": statistic, "df": df, "p_raw": float(chi2.sf(statistic, df)),
        "weighted_negative_loglikelihood": float(objective(beta)),
    }
    assert out["gradient_max"] < 1e-6
    assert out["hessian_min_eigenvalue"] > 0
    if not predictions:
        return out

    def standardized(a, b):
        altered = frame.copy()
        altered[PUBLIC] = a
        altered[POLICE] = b
        xx = design(altered)
        prob = probabilities(beta, xx)
        mean = np.average(prob, weights=w, axis=0)
        jac = np.zeros((3, 2*p))
        for j in range(3):
            for k in range(2):
                jac[j, k*p:(k+1)*p] = np.average(
                    (prob[:, j] * ((j == k) - prob[:, k]))[:, None] * xx,
                    weights=w, axis=0)
        return mean, jac

    configurations = {}
    cache = {}
    for a, b in itertools.product(prediction_levels, repeat=2):
        mu, jac = standardized(a, b)
        var = jac @ covariance @ jac.T
        se = np.sqrt(np.maximum(np.diag(var), 0))
        key = f"public_{a}_police_{b}"
        cache[a, b] = (mu, jac)
        configurations[key] = {"observed_n": int(((frame[PUBLIC] == a) & (frame[POLICE] == b)).sum()),
                               "probability": mu.tolist(),
                               "ci95_pointwise": np.column_stack([mu - 1.96*se, mu + 1.96*se]).tolist()}
    contrasts = {}
    for police in [1, 2]:
        mu = cache[1, police][0] - cache[2, police][0]
        jac = cache[1, police][1] - cache[2, police][1]
        se = np.sqrt(np.maximum(np.diag(jac @ covariance @ jac.T), 0))
        contrasts[f"public_major_minus_minor_at_police_{police}"] = {
            "difference": mu.tolist(), "ci95_pointwise":
            np.column_stack([mu - 1.96*se, mu + 1.96*se]).tolist()}
    mu = (cache[1, 1][0] - cache[2, 1][0]) - (cache[1, 2][0] - cache[2, 2][0])
    jac = (cache[1, 1][1] - cache[2, 1][1]) - (cache[1, 2][1] - cache[2, 2][1])
    se = np.sqrt(np.maximum(np.diag(jac @ covariance @ jac.T), 0))
    contrasts["difference_of_differences"] = {
        "difference": mu.tolist(), "ci95_pointwise":
        np.column_stack([mu - 1.96*se, mu + 1.96*se]).tolist(),
        "p_raw": (2 * norm.sf(np.abs(mu / se))).tolist()}
    out["outcome_order"] = OUTCOME_ORDER
    out["configurations"] = configurations
    out["contrasts"] = contrasts
    return out


def holm(rows):
    prev = 0.0
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p_raw"])
    for rank, index in enumerate(order):
        prev = max(prev, min(1.0, (len(rows) - rank) * rows[index]["p_raw"]))
        rows[index]["p_holm6"] = prev


def main():
    frame, _ = pyreadstat.read_sav(str(SOURCE))
    frame = frame.loc[frame["FORM_W99"].eq(1)].replace(99, np.nan)
    pairs = [(PUBLIC, POLICE), (PUBLIC, GOVERNMENT), (PUBLIC, DEVELOPER),
             (POLICE, GOVERNMENT), (POLICE, DEVELOPER), (GOVERNMENT, DEVELOPER)]
    benchmark = []
    for pair in pairs:
        row = fit(frame, pair)
        benchmark.append(row)
        print("pair", pair, row["n"], row["wald"], row["p_raw"], flush=True)
    assert len({row["n"] for row in benchmark}) == 1
    assert benchmark[0]["n"] == 4752
    holm(benchmark)
    primary = json.loads((OUT / "configuration_models.json").read_text())
    initial = primary["overall_interaction"]["interaction_test"]
    assert abs(benchmark[0]["wald"] - initial["Wald"]) < 1e-6
    assert abs(benchmark[0]["p_raw"] - initial["p"]) < 1e-9

    eligible = frame.dropna(subset=[OUTCOME, *ROLES, *CONTROLS])
    restricted = eligible.loc[eligible[PUBLIC].isin([1, 2]) & eligible[POLICE].isin([1, 2])]
    sensitivity = fit(restricted, (PUBLIC, POLICE), predictions=True)
    assert sensitivity["df"] == 2
    output = {"analysis_status": "exploratory supplementary benchmark and sensitivity",
              "method": "weighted multinomial logit, individual-score HC0 sandwich; final weights rescaled to mean one",
              "primary_family_unchanged": True,
              "benchmark_holm_family_size": 6,
              "benchmark": benchmark,
              "major_minor_sensitivity": sensitivity,
              "major_minor_excluded_from_main_n": int(len(eligible) - len(restricted))}
    DEST.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("sensitivity", sensitivity["n"], sensitivity["wald"], sensitivity["p_raw"], flush=True)
    print("wrote", DEST, flush=True)


if __name__ == "__main__":
    main()

