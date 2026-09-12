"""Deterministic SciPy/statsmodels analyses selected by the agent."""
import warnings

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

from app.tools.python_tool import load_frame, prepare_frame, json_result

METHODS = {"pearson", "spearman", "welch_ttest", "chi_square", "ols"}


def analyze_statistics(file_path, sql, method, x, y="", predictors=None):
    if method not in METHODS:
        raise ValueError(f"Choose a supported method: {', '.join(sorted(METHODS))}.")
    frame = load_frame(file_path, sql)
    predictors = predictors or []
    if method == "ols":
        if not 1 <= len(predictors) <= 12 or len(set(predictors)) != len(predictors):
            raise ValueError("OLS requires 1-12 distinct numeric predictors.")
        if y in predictors:
            raise ValueError("The outcome cannot also be a predictor.")
        columns, numeric = [y, *predictors], [y, *predictors]
    else:
        if x == y:
            raise ValueError("Choose two different columns.")
        columns = [x, y]
        numeric = [x, y] if method in {"pearson", "spearman"} else ([y] if method == "welch_ttest" else [])
    clean, excluded = prepare_frame(frame, columns, numeric)
    caveats = [
        "Results describe the rows selected by the SQL query; they do not establish causation.",
        "Inference assumes independent observations and an appropriate sampling design; these are not verified automatically.",
        "P-values are exploratory and are not adjusted for testing multiple hypotheses.",
    ]
    output = {
        "method": method, "input_rows": len(frame), "rows_used": len(clean),
        "rows_excluded": excluded, "caveats": caveats,
    }
    if excluded:
        caveats.append("Rows with missing or invalid selected values were excluded; this may bias the result.")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if method in {"pearson", "spearman"}:
            if len(clean) < 4 or any(clean[c].nunique() < 2 for c in columns):
                raise ValueError("Correlation requires at least four usable pairs and two nonconstant columns.")
            test = (stats.pearsonr if method == "pearson" else stats.spearmanr)(clean[x], clean[y])
            row = {"relationship": f"{x} and {y}", "coefficient": test.statistic, "p_value": test.pvalue}
            if method == "pearson":
                interval = test.confidence_interval(confidence_level=0.95)
                row.update(ci_95_low=interval.low, ci_95_high=interval.high)
                caveats.append("Pearson measures a linear relationship and is sensitive to outliers; its interval uses a normality approximation.")
            else:
                caveats.append("Spearman measures a monotonic rank relationship; its approximate p-value can be inaccurate for small samples.")
            output["rows"] = [row]
        elif method == "welch_ttest":
            groups = list(clean[x].unique())
            if len(groups) != 2:
                raise ValueError("Welch's test requires exactly two groups in x and a numeric outcome y.")
            a, b = (clean.loc[clean[x] == group, y] for group in groups)
            if min(len(a), len(b)) < 2 or a.var() / len(a) + b.var() / len(b) <= 0:
                raise ValueError("Each group needs at least two rows, with nonzero combined variance.")
            test = stats.ttest_ind(a, b, equal_var=False)
            interval = test.confidence_interval(confidence_level=0.95)
            output["rows"] = [{
                "group_a": str(groups[0]), "group_b": str(groups[1]),
                "n_a": len(a), "n_b": len(b), "mean_a": a.mean(), "mean_b": b.mean(),
                "difference_a_minus_b": a.mean() - b.mean(),
                "ci_95_low": interval.low, "ci_95_high": interval.high,
                "t_statistic": test.statistic, "degrees_of_freedom": test.df,
                "p_value": test.pvalue,
            }]
            caveats.append("Welch compares independent group means with unequal variances; small skewed samples or outliers can make inference unreliable. It is not a paired test.")
        elif method == "chi_square":
            if any(not 2 <= clean[c].nunique() <= 20 for c in columns):
                raise ValueError("Chi-square requires 2-20 categories in each column, one observation per row.")
            table = pd.crosstab(clean[x], clean[y])
            statistic, pvalue, dof, expected = stats.chi2_contingency(table, correction=False)
            sparse = bool((expected < 5).any())
            output["rows"] = [{
                "chi_square": statistic, "degrees_of_freedom": dof,
                "p_value": None if sparse else pvalue,
                "cramers_v": np.sqrt(statistic / (len(clean) * (min(table.shape) - 1))),
                "minimum_expected_count": expected.min(),
            }]
            if sparse:
                caveats.append("Some expected counts are below five; the approximate p-value is withheld. A suitable exact test or justified regrouping is needed.")
            caveats.append("Cramer's V describes categorical association, not direction; it is not bias-corrected.")
        else:
            if len(clean) < max(10, len(predictors) + 3):
                raise ValueError("OLS needs at least 10 rows and more observations than fitted parameters.")
            if any(clean[c].nunique() < 2 for c in columns):
                raise ValueError("OLS outcome and predictors must be nonconstant.")
            design = sm.add_constant(clean[predictors].to_numpy(dtype=float), has_constant="add")
            if np.linalg.matrix_rank(design) < design.shape[1]:
                raise ValueError("Predictors are linearly dependent. Remove redundant predictors.")
            base = sm.OLS(clean[y].to_numpy(dtype=float), design).fit()
            condition_number = base.condition_number
            if np.any(base.get_influence().hat_matrix_diag >= 1 - 1e-10):
                raise ValueError("An observation has excessive leverage; robust intervals cannot be estimated reliably.")
            fitted = base.get_robustcov_results(cov_type="HC3")
            intervals = fitted.conf_int(alpha=0.05)
            output.update(r_squared=fitted.rsquared, adjusted_r_squared=fitted.rsquared_adj)
            output["rows"] = [{
                "term": name, "coefficient": fitted.params[i], "standard_error": fitted.bse[i],
                "ci_95_low": intervals[i, 0], "ci_95_high": intervals[i, 1],
                "p_value": fitted.pvalues[i],
            } for i, name in enumerate(["Intercept", *predictors])]
            caveats.append("OLS fits a linear additive model with HC3 robust standard errors. Coefficients hold included predictors constant; their raw magnitudes cannot rank predictors with different units. R-squared is in-sample fit, not prediction accuracy.")
            if condition_number > 1e8:
                caveats.append("The design is poorly conditioned; scaling or correlated predictors may make estimates unstable.")
        caveats.extend(dict.fromkeys(str(item.message)[:300] for item in caught))
    return json_result(output)
