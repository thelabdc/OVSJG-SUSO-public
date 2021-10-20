"""
This file contains tools for doing A/B Testing.
@author Kevin H. Wilson <kevin.wilson@dc.gov>
"""
import numpy as np
from scipy import special
from scipy.stats import binom


def degree_of_certainty(successes_a, failures_a, successes_b, failures_b):
    """
    Compute the "degree of certainty" that the B side of an A/B test is better
    than the A side when the outcome is binary. Literally, this returns::
      Pr(p_b > p_a)
    where `p_g` is the probability of a "success" in condition `g \in {a, b}`.
    Here, we assume that `p_a` and `p_b` are random variables over [0, 1]. We
    assume they are independent (indeed, really over entirely distinct probability
    spaces). We take a prior that `p_g` is distributed as `Beta(1, 1)`, i.e., the
    uniform distribution. Thus, after `successes_g` successes and `failures_g`
    failures, the posterior of `p_g` is::
      p_g ~ Beta(successes_g + 1, failures_g + 1).
    This allows us to compute `Pr(p_b > p_a)`. This works out to be::
      sum_{j = 0}^{successes_b + 1}
                     B(1 + successes_a + j, failures_a + failures_b + 2)
          -----------------------------------------------------------------------------
          (1 + failures_b + j) B(1 + j, 1 + failures_b) B(success_a + 1, failures_a + 1)
    where B(a, b) is the beta function.
    For more details, see
      http://www.evanmiller.org/bayesian-ab-testing.html
    Args:
      successes_a (int): The number of successes in condition A
      failures_a (int): The number of failures in condition A
      successes_b (int): The number of successes in condition B
      failures_b (int): The number of failures in condition B
    """
    the_range = np.arange(successes_b + 1)
    conditional_a = special.betaln(successes_a + 1, failures_a + 1)

    return np.sum(
        np.exp(
            special.betaln(1 + successes_a + the_range, failures_a + failures_b + 2)
            - np.log(1 + failures_b + the_range)
            - special.betaln(1 + the_range, 1 + failures_b)
            - conditional_a
        )
    )


def degree_of_certainty_draws(
    base_rate,
    treatment_rate,
    num_participants=None,
    num_control=None,
    num_treatment=None,
    num_draws=1000,
):
    """
    Draw num_draws from the distribution of the degree of certainty given an assumed
    base rate and treatment rate. You must provide either num_partipicants OR num_control
    and num_treatment.
    Args:
      base_rate (float): The assumed rate at which the control group registers a success
      treatment_rate (float): The assumed rate at which the treatment group registers a success
      num_participants (int|None): The number of participants in the experiment. Assumes both
        control and treatment have equal numbers of participants. If None, must provide BOTH
        num_control and num_treatment
      num_control (int|None): The number of participants in the control group. If provided,
        must also provide num_treatment
      num_treatment (int|None): The number of participants in the treatment group. If provided,
        must also provide num_control
      num_draws (int): The number of draws from the degree of certainty distribution
    Returns:
      np.ndarray[float]: The drawn degrees of certainty
    """
    if num_participants:
        num_control = num_participants // 2
        num_treatment = num_participants - num_control
    else:
        if not (num_base and num_treatment):
            raise ValueError(
                "If you provide num_control or num_treatment you must provide the other"
            )

    #     num_control = num_participants // 2
    #     num_treatment = num_participants - num_control

    successes_control = binom.rvs(num_control, base_rate, size=num_draws)
    failures_control = num_participants - successes_control

    successes_treatment = binom.rvs(num_treatment, treatment_rate, size=num_draws)
    failures_treatment = num_participants - successes_treatment

    return np.array(
        [
            degree_of_certainty(s_control, f_control, s_treatment, f_treatment)
            for s_control, f_control, s_treatment, f_treatment in zip(
                successes_control,
                failures_control,
                successes_treatment,
                failures_treatment,
            )
        ]
    )
