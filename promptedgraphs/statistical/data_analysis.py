"""This document helps understand
the data types and distributions of various data sets."""

import concurrent.futures
import os
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats
import seaborn as sns
import tqdm
from scipy.stats import kstest

from promptedgraphs.vis import get_colors

# from scipy.stats
DISCRETE_DISTRIBUTIONS = [
    "bernoulli",  # -- Bernoulli
    "betabinom",  # -- Beta-Binomial
    "binom",  # -- Binomial
    "boltzmann",  # -- Boltzmann (Truncated Discrete Exponential)
    "dlaplace",  # -- Discrete Laplacian
    "geom",  # -- Geometric
    "hypergeom",  # -- Hypergeometric
    "logser",  # -- Logarithmic (Log-Series, Series)
    "nbinom",  # -- Negative Binomial
    "nchypergeom_fisher",  # Fisher's Noncentral Hypergeometric
    "nchypergeom_wallenius",  # Wallenius's Noncentral Hypergeometric
    "nhypergeom",  # -- Negative Hypergeometric
    "planck",  # -- Planck (Discrete Exponential)
    "poisson",  # -- Poisson
    "randint",  # -- Discrete Uniform
    "skellam",  # -- Skellam
    "yulesimon",  # -- Yule-Simon
    "zipf",  # -- Zipf (Zeta)
    "zipfian",  # -- Zipfian
]
CONTINUOUS_DISTRIBUTIONS = [
    "alpha",  # -- Alpha
    "anglit",  # -- Anglit
    "arcsine",  # -- Arcsine
    "argus",  # -- Argus
    "beta",  # -- Beta
    "betaprime",  # -- Beta Prime
    "bradford",  # -- Bradford
    "burr",  # -- Burr (Type III)
    "burr12",  # -- Burr (Type XII)
    "cauchy",  # -- Cauchy
    "chi",  # -- Chi
    "chi2",  # -- Chi-squared
    "cosine",  # -- Cosine
    "crystalball",  # Crystalball
    "dgamma",  # -- Double Gamma
    "dweibull",  # -- Double Weibull
    "erlang",  # -- Erlang
    "expon",  # -- Exponential
    "exponnorm",  # -- Exponentially Modified Normal
    "exponweib",  # -- Exponentiated Weibull
    "exponpow",  # -- Exponential Power
    "f",  # -- F (Snecdor F)
    "fatiguelife",  # Fatigue Life (Birnbaum-Saunders)
    "fisk",  # -- Fisk
    "foldcauchy",  # -- Folded Cauchy
    "foldnorm",  # -- Folded Normal
    "genlogistic",  # Generalized Logistic
    "gennorm",  # -- Generalized normal
    "genpareto",  # -- Generalized Pareto
    "genexpon",  # -- Generalized Exponential
    "genextreme",  # -- Generalized Extreme Value
    "gausshyper",  # -- Gauss Hypergeometric
    "gamma",  # -- Gamma
    "gengamma",  # -- Generalized gamma
    "genhalflogistic",  # Generalized Half Logistic
    # "genhyperbolic",  # Generalized Hyperbolic
    # "geninvgauss",  # Generalized Inverse Gaussian
    "gibrat",  # -- Gibrat
    "gompertz",  # -- Gompertz (Truncated Gumbel)
    "gumbel_r",  # -- Right Sided Gumbel, Log-Weibull, Fisher-Tippett, Extreme Value Type I
    "gumbel_l",  # -- Left Sided Gumbel, etc.
    "halfcauchy",  # -- Half Cauchy
    "halflogistic",  # Half Logistic
    "halfnorm",  # -- Half Normal
    "halfgennorm",  # Generalized Half Normal
    "hypsecant",  # -- Hyperbolic Secant
    "invgamma",  # -- Inverse Gamma
    "invgauss",  # -- Inverse Gaussian
    "invweibull",  # -- Inverse Weibull
    "johnsonsb",  # -- Johnson SB
    "johnsonsu",  # -- Johnson SU
    "kappa4",  # -- Kappa 4 parameter
    "kappa3",  # -- Kappa 3 parameter
    "ksone",  # -- Distribution of Kolmogorov-Smirnov one-sided test statistic
    # "kstwo",  # -- Distribution of Kolmogorov-Smirnov two-sided test statistic
    "kstwobign",  # -- Limiting Distribution of scaled Kolmogorov-Smirnov two-sided test statistic.
    "laplace",  # -- Laplace
    "laplace_asymmetric",  # Asymmetric Laplace
    "levy",  # -- Levy
    "levy_l",  #
    # "levy_stable",  #
    "logistic",  # -- Logistic
    "loggamma",  # -- Log-Gamma
    "loglaplace",  # -- Log-Laplace (Log Double Exponential)
    "lognorm",  # -- Log-Normal
    "loguniform",  # -- Log-Uniform
    "lomax",  # -- Lomax (Pareto of the second kind)
    "maxwell",  # -- Maxwell
    "mielke",  # -- Mielke's Beta-Kappa
    "moyal",  # -- Moyal
    "nakagami",  # -- Nakagami
    # "ncx2",  # -- Non-central chi-squared
    # "ncf",  # -- Non-central F
    # "nct",  # -- Non-central Student's T
    "norm",  # -- Normal (Gaussian)
    # "norminvgauss",  # Normal Inverse Gaussian
    "pareto",  # -- Pareto
    "pearson3",  # -- Pearson type III
    "powerlaw",  # -- Power-function
    "powerlognorm",  # Power log normal
    "powernorm",  # -- Power normal
    "rdist",  # -- R-distribution
    "rayleigh",  # -- Rayleigh
    "rel_breitwigner",  # Relativistic Breit-Wigner
    "rice",  # -- Rice
    "recipinvgauss",  # Reciprocal Inverse Gaussian
    "semicircular",  # Semicircular
    "skewcauchy",  # -- Skew Cauchy
    "skewnorm",  # -- Skew normal
    # "studentized_range",  # Studentized Range
    "t",  # -- Student's T
    "trapezoid",  # -- Trapezoidal
    "triang",  # -- Triangular
    "truncexpon",  # -- Truncated Exponential
    "truncnorm",  # -- Truncated Normal
    "truncpareto",  # Truncated Pareto
    "truncweibull_min",  # Truncated minimum Weibull distribution
    # "tukeylambda",  # Tukey-Lambda
    "uniform",  # -- Uniform
    "vonmises",  # -- Von-Mises (Circular)
    "vonmises_line",  # Von-Mises (Line)
    "wald",  # -- Wald
    "weibull_min",  # Minimum Weibull (see Frechet)
    "weibull_max",  # Maximum Weibull (see Frechet)
    "wrapcauchy",  # -- Wrapped Cauchy
]


def can_cast_to_ints_without_losing_precision_np_updated(values: list[float|int], epsilon=1e-9):
    """
    Check if all values in the list can be safely cast to integers without losing precision using NumPy,
    allowing for a small epsilon deviation from integer numbers to handle floating point errors.

    Args:
    - values (list or numpy.ndarray): A list or numpy array of values to check.
    - epsilon (float): The tolerance for deviation from an exact integer, to handle floating point errors.

    Returns:
    - bool: True if all values can be safely cast to integers without significant loss of precision, False otherwise.
    """
    np_values = np.array(
        values
    )  # Convert the list to a NumPy array if it's not already one
    try:
        fractional_parts = np.abs(np_values - np.round(np_values))
    except TypeError:
        return False
    return np.all(fractional_parts <= epsilon)


# Function to fit distribution and perform KS test
def _fit_and_test(data, dist):
    try:
        t = time.time()
        dist_params = getattr(scipy.stats, dist).fit(data)
        fit_time = time.time() - t
        ks_statistic, p_value = kstest(data, dist, args=dist_params)
        result = {
            "Parameters": dist_params,
            "KS-Test": ks_statistic,
            "P-Value": p_value,
            "fit_time": fit_time,
        }
        return (dist, result)
    except Exception as e:
        return (dist, f"Error fitting {dist}: {e}")


def fit_distribution(
    data: np.array,
    discrete_or_continuous: str | None = None,
    max_workers: int | None = None,
):
    # max_workers is num cores by default
    if max_workers is None or max_workers < 1:
        max_workers = max_workers or int(os.cpu_count() / 2)
    assert discrete_or_continuous in ["discrete", "continuous", None], (  # noqa
        "discrete_or_continuous must be one of the following: "
        "['discrete', 'continuous', None]"
    )
    if discrete_or_continuous is None:
        discrete_or_continuous = (
            "discrete"
            if can_cast_to_ints_without_losing_precision_np_updated(data)
            else "continuous"
        )
    if discrete_or_continuous == "discrete":
        dists = DISCRETE_DISTRIBUTIONS
    else:
        dists = CONTINUOUS_DISTRIBUTIONS

    np.random.shuffle(dists)
    fit_results = {}

    # Use ProcessPoolExecutor to parallelize fitting
    fit_results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Map the function over the distributions
        futures = {executor.submit(_fit_and_test, data, dist): dist for dist in dists}
        ittr = tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(dists))
        for future in ittr:
            dist = futures[future]
            try:
                result = future.result(timeout=10)  # 30-second timeout for each task
                if isinstance(result[1], dict):
                    fit_results[result[0]] = result[1]
                    # Optionally print current best fits
                    print("Remaining:", sorted(set(dists) - set(fit_results.keys())))
                    # print(
                    # .T.sort_values("KS-Test", ascending=True)
                    # .head(10)
                else:
                    print(result[1])  # Print error message
            except concurrent.futures.TimeoutError:
                print(f"TimeoutError: Fitting {dist} exceeded 30 seconds.")

    # for dist in ittr:
    # # Fit the data to various distributions and estimate their parameters
    # # Kolmogorov-Smirnov test for goodness-of-fit
    # # Results
    # fit_results[dist] = {
    # "KS-Test": ks_statistic,
    # "P-Value": p_value,
    # print(
    # .T.sort_values("KS-Test", ascending=True)
    # .head(10)

    return fit_results


def plot_fitted(data, results: pd.DataFrame, top_n=5):
    # Re-import necessary libraries and re-define variables after reset
    # Re-fit parameters for selected distributions
    results = results.sort_values("KS-Test", ascending=True).head(top_n)

    # Create a range of values for plotting fitted distributions
    x_values = np.linspace(min(data), max(data), 1000)

    # Plotting
    plt.figure(figsize=(14, 8))
    sns.histplot(
        data,
        kde=True,
        bins=30,
        color="gray",
        stat="density",
        label="Empirical",
        alpha=0.5,
    )

    colors = get_colors(results.index.tolist())
    for dist_name, row in results.iterrows():
        print("plotting", dist_name)
        dist_params = row["Parameters"]
        pdf = getattr(scipy.stats, dist_name).pdf(x_values, *dist_params)
        plt.plot(
            x_values, pdf, label=dist_name, color=colors[dist_name][:7], linestyle="--"
        )

    plt.title("Empirical Distribution with Fitted Distributions")
    plt.xlabel("Value")
    plt.ylabel("Density")
    plt.legend()
    plt.show()


def get_posterior_weights(
    data: np.ndarray, results: pd.DataFrame, priors: dict[str, float] = None
):
    uniform_prior = 1 / len(results)
    default_priors = {dist: uniform_prior for dist in results.index}
    priors = priors or default_priors
    len(data)
    log_pdfs = {}
    for dist_name, row in results.iterrows():
        dist_params = row["Parameters"]
        pdf = getattr(scipy.stats, dist_name).pdf(data, *dist_params)
        log_pdfs[dist_name] = np.log(pdf).sum() / len(data)
        if np.isinf(log_pdfs[dist_name]) or np.isnan(log_pdfs[dist_name]):
            log_pdfs[dist_name] = -np.inf

    Z = sum(priors[dist] * np.exp(log_pdf) for dist, log_pdf in log_pdfs.items())
    return {
        dist: priors[dist] * np.exp(log_pdf) / Z for dist, log_pdf in log_pdfs.items()
    }


if __name__ == "__main__":
    # Load the data
    import json

    with open(
        "/usr/local/repos/thecrowdsline/thecrowdsline-data/nfl_roster.jsonl"
    ) as f:
        data = pd.DataFrame(json.loads(line) for line in f.readlines())

    # Fit the data to various distributions
    c = "age"
    c = "entry_year"
    c = "draft_number"
    x = data[c].dropna().values
    dists = fit_distribution(x, discrete_or_continuous="continuous", max_workers=4)

    df = pd.DataFrame(dists).T
    top_dists = df.loc[df["KS-Test"] < 0.05]
    if len(top_dists) > 0:
        print(top_dists)
    plot_fitted(x, top_dists, top_n=len(top_dists))
    weights = get_posterior_weights(x, top_dists)
    print(top_dists.join(pd.Series(weights, name="Posterior Weight")))
    print(dists)
