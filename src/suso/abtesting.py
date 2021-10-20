## load imports
import itertools

import numpy as np
import pandas as pd
import scipy
from scipy import special
from scipy.stats import binom, gamma


def degree_of_certainty(successes_a, failures_a, successes_b, failures_b):
    the_range = np.arange(successes_b + 1)
    # print("The range of possible successes in tx group based on prior is: " + str(np.arange(successes_b + 1).flatten()))

    # posterior for control group (observed count of successes in control group + prior; observed count of failures + prior)
    conditional_a = scipy.special.betaln(successes_a + 1, failures_a + 1)
    # print("The beta dist value for control group conditional on prior is: " + str(conditional_a))
    return np.sum(
        np.exp(
            scipy.special.betaln(
                1 + successes_a + the_range, failures_a + failures_b + 2
            )
            - np.log(1 + failures_b + the_range)
            - scipy.special.betaln(1 + the_range, 1 + failures_b)
            - conditional_a
        )
    )


def degree_of_certainty_draws_perc(
    base_rate,
    treatment_rate,
    num_participants=None,
    num_control=None,
    num_treatment=None,
    num_draws=1000,
    tx_greater=True,
    seed=9252018,
):
    if num_participants:
        num_control = num_participants // 2
        num_treatment = num_participants - num_control
    else:
        if not (num_control and num_treatment):
            raise ValueError(
                "If you provide num_control or num_treatment you must provide the other"
            )

    ## set seed
    random = np.random.RandomState(seed)

    successes_control = binom.rvs(num_control, base_rate, size=num_draws)
    failures_control = num_participants - successes_control

    successes_treatment = binom.rvs(num_treatment, treatment_rate, size=num_draws)
    failures_treatment = num_participants - successes_treatment
    results_alldraws = np.array(
        [
            degree_of_certainty(
                successes_control,
                failures_control,
                successes_treatment,
                failures_treatment,
            )
            for successes_control, failures_control, successes_treatment, failures_treatment in zip(
                successes_control,
                failures_control,
                successes_treatment,
                failures_treatment,
            )
        ]
    )

    if tx_greater == True:
        perc_overthreshold = len(results_alldraws[results_alldraws >= 0.95]) / len(
            results_alldraws
        )
        return perc_overthreshold
    elif tx_greater == False:
        results_reversed = 1 - results_alldraws
        perc_overthreshold = len(results_reversed[results_reversed >= 0.95]) / len(
            results_reversed
        )
        return perc_overthreshold


def degree_of_certainty_draws_forwriteup(
    base_rate,
    treatment_rate,
    successes_control,
    successes_treatment,
    failures_control,
    failures_treatment,
    num_participants=None,
    num_control=None,
    num_treatment=None,
    num_draws=1000,
    tx_greater=True,
    seed=9252018,
):
    if num_participants:
        num_control = num_participants // 2
        num_treatment = num_participants - num_control
    else:
        if not (num_control and num_treatment):
            raise ValueError(
                "If you provide num_control or num_treatment you must provide the other"
            )

    ## set seed
    random = np.random.RandomState(seed)

    successes_control = binom.rvs(num_control, base_rate, size=num_draws)
    failures_control = num_control - successes_control

    successes_treatment = binom.rvs(num_treatment, treatment_rate, size=num_draws)
    failures_treatment = num_treatment - successes_treatment

    ## for similar with other projects, get beta distribution
    ## to find and return posterior
    beta_control = random.beta(successes_control + 1, failures_control, size=num_draws)
    beta_treatment = random.beta(
        successes_treatment + 1, failures_treatment, size=num_draws
    )
    posterior = beta_treatment - beta_control
    posterior.sort()

    ## calculate probability across all draws
    results_alldraws = np.array(
        [
            degree_of_certainty(
                successes_control,
                failures_control,
                successes_treatment,
                failures_treatment,
            )
            for successes_control, failures_control, successes_treatment, failures_treatment in zip(
                successes_control,
                failures_control,
                successes_treatment,
                failures_treatment,
            )
        ]
    )

    if tx_greater == True:
        perc_overthreshold = len(results_alldraws[results_alldraws >= 0.95]) / len(
            results_alldraws
        )
        return (perc_overthreshold, results_alldraws, posterior)
    elif tx_greater == False:
        results_reversed = 1 - results_alldraws
        perc_overthreshold = len(results_reversed[results_reversed >= 0.95]) / len(
            results_reversed
        )
        return (perc_overthreshold, results_reversed, posterior)


def degree_of_certainty_counts(
    events_control, exposure_control, events_tx, exposure_tx
):

    """
    Compute a single "degree of certainty" that the treatment side of a test is better
    than the control side when the outcome is count data of the form events and exposures. This returns:

    Pr(gamma_treatment > gamma_control)

    where gamma is the count of events adjusting for the (logged) exposure (a poisson parameter composed of alpha = events,
    beta = exposure, assumed to follow a gamma distribution)

    For more details, see http://www.evanmiller.org/bayesian-ab-testing.html

    Args:
    @ events_control (int): The total count of events in control group
    @ exposure_control (int): Total exposure for the control group (e.g., if events is # of school days missed, exposure is
    @ duration at which the control group is at risk for missing school)
    @ events_tx (int): The count of events in treatment group
    @ exposure_tx (int): The exposure for the treatment group
    """

    ###
    k_range = np.arange(0 + events_control - 1)
    logbeta_count_tx = scipy.special.betaln(k_range + 1, events_tx)
    log_count_tx_prior = np.log(k_range + events_tx)
    log_exposure_tx_control = np.log(exposure_tx + exposure_control)
    count_tx_prior = k_range + events_tx
    log_exposure_tx = np.log(exposure_tx)
    log_exposure_control = np.log(exposure_control)
    inside_exp = (
        k_range * log_exposure_control
        + events_tx * log_exposure_tx
        - count_tx_prior * log_exposure_tx_control
        - log_count_tx_prior
        - logbeta_count_tx
    )
    return 1 - np.sum(np.exp(inside_exp))


def degree_of_certainty_count_draws_perc(
    control_events_per_obs,
    treatment_events_per_obs,
    control_exposure_per_obs,
    treatment_exposure_per_obs,
    num_participants=None,
    num_control=None,
    num_treatment=None,
    num_draws=1000,
    tx_greater=True,
    seed=9252018,
):

    """
    The function degree of certainty counts returns the probability treatment > control for a single
    pair of event/exposure values.

    The present function generalizes that code to return a distribution of values rather than
    a single values. It:

    Gnerates a distribution of events counts by: 1) starting with the observed count
    2) drawing from a gamma distribution num_draws times to return an array
    of event counts that are near that observed count but exhibit random variation
    3) feeds each element in that array, along with the exposure values, to the
    degree of certainty counts function to return a num_draws-length array of
    probabilities tx > control
    4) if our quantity of interest is pr tx > control, returns the percentage of
    draws where that probability is 0.95 or greater
    5) if our quantity of interest is pr tx < control (e.g., the treatment reduced counts of some
    bad event, finds that probability as Pr(tx < control) = 1 - Pr(tx > control), and calculates
    that same percentage
    6) returns the percentage (for well-powered, want 80% of above)

    Returns: list of percentages; each element in the list corresponds to one combination
    of effect, sample size, and base rates
    """

    ## get n in each group
    if num_participants:
        num_control = num_participants // 2
        num_treatment = num_participants - num_control
    else:
        if not (num_control and num_treatment):
            raise ValueError(
                "If you provide num_control or num_treatment you must provide the other"
            )

    ## get total counts as n_count_perobs * nobs_pergroup
    events_control_predraws = control_events_per_obs * num_control
    events_treatment_predraws = treatment_events_per_obs * num_treatment
    events_control_draws = gamma.rvs(events_control_predraws, size=num_draws)
    events_treatment_draws = gamma.rvs(events_treatment_predraws, size=num_draws)

    ## didn't introduce randomness into the exposure
    exposure_control = control_exposure_per_obs * num_control
    exposure_treatment = treatment_exposure_per_obs * num_treatment

    ## create an iterable with draws of events + exposure (no random variation added)
    draws_iterateover = zip(
        events_control_draws,
        itertools.repeat(exposure_control, num_draws),
        events_treatment_draws,
        itertools.repeat(exposure_treatment, num_draws),
    )

    ## Apply function to that stored option
    results_alldraws = np.array(
        [
            degree_of_certainty_counts(
                events_control, exposure_control, events_tx, exposure_tx
            )
            for events_control, exposure_control, events_tx, exposure_tx in draws_iterateover
        ]
    )

    ## find percentage of certainty 0.95 and greater
    if tx_greater == True:
        perc_overthreshold = len(results_alldraws[results_alldraws >= 0.95]) / len(
            results_alldraws
        )
        return perc_overthreshold
    elif tx_greater == False:
        results_reversed = 1 - results_alldraws
        perc_overthreshold = len(results_reversed[results_reversed >= 0.95]) / len(
            results_reversed
        )
        return perc_overthreshold

    return results_alldraws


def degree_of_certainty_count_draws_forwriteup(
    control_events,
    treatment_events,
    control_exposure,
    treatment_exposure,
    num_draws=1000,
    tx_greater=True,
    seed=9252018,
):

    """
    The function degree of certainty counts returns the probability treatment > control for a single
    pair of event/exposure values.

    The present function generalizes that code to return a distribution of values rather than
    a single values. It:

    Gnerates a distribution of events counts by: 1) starting with the observed count
    2) drawing from a gamma distribution num_draws times to return an array
    of event counts that are near that observed count but exhibit random variation
    3) feeds each element in that array, along with the exposure values, to the
    degree of certainty counts function to return a num_draws-length array of
    probabilities tx > control
    4) if our quantity of interest is pr tx > control, returns the percentage of
    draws where that probability is 0.95 or greater
    5) if our quantity of interest is pr tx < control (e.g., the treatment reduced counts of some
    bad event, finds that probability as Pr(tx < control) = 1 - Pr(tx > control), and calculates
    that same percentage
    6) returns the percentage (for well-powered, want 80% of above)

    Returns: list of percentages; each element in the list corresponds to one combination
    of effect, sample size, and base rates
    """

    ## get total counts as n_count_perobs * nobs_pergroup
    events_control_predraws = control_events
    events_treatment_predraws = treatment_events
    events_control_draws = gamma.rvs(events_control_predraws, size=num_draws)
    events_treatment_draws = gamma.rvs(events_treatment_predraws, size=num_draws)

    ## didn't introduce randomness into the exposure
    exposure_control = control_exposure
    exposure_treatment = treatment_exposure

    ## return posterior rates
    posterior_rates = (events_treatment_draws / treatment_exposure) * 14 - (
        events_control_draws / control_exposure
    ) * 14
    posterior_rates.sort()

    ## create an iterable with draws of events + exposure (no random variation added)
    draws_iterateover = zip(
        events_control_draws,
        itertools.repeat(exposure_control, num_draws),
        events_treatment_draws,
        itertools.repeat(exposure_treatment, num_draws),
    )

    ## Apply function to that stored option
    results_alldraws = np.array(
        [
            degree_of_certainty_counts(
                events_control, exposure_control, events_tx, exposure_tx
            )
            for events_control, exposure_control, events_tx, exposure_tx in draws_iterateover
        ]
    )

    ## find percentage of certainty 0.95 and greater
    if tx_greater == True:
        perc_overthreshold = len(results_alldraws[results_alldraws >= 0.95]) / len(
            results_alldraws
        )
        return (perc_overthreshold, results_alldraws, posterior_rates)
    elif tx_greater == False:
        results_reversed = 1 - results_alldraws
        perc_overthreshold = len(results_reversed[results_reversed >= 0.95]) / len(
            results_reversed
        )
        return (perc_overthreshold, results_reversed, posterior_rates)


def create_combinations_certanalysis(sample_sizes, effect_sizes, base_rates):

    """
    Helper function to speed up process of analyzing power over many
    sample and effect sizes.
    Args:
    @sample_size: list of sample sizes to investigate
    @effect_size: list of effect sizes to investigate
    @base_rates: list of base rates to investigate

    Note that if you want to hold one of these fixed while varying the
    others, you can just enter a single element list
    and that will repeat for all the variations of the other parameters
    (e.g., same base rate at all effect and sample sizes)

    Returns list where each element is a tuple
    Tuple order is: (N, effect size, base_rate)
    """

    return list(itertools.product(sample_sizes, effect_sizes, base_rates))


def find_probability_acrossdraws(
    one_combo, type_of_outcome, direction, num_draws, exposure=None
):

    """
    Function to speed up power analyses
    Input is one combination of sample size, effect size, and base rate
    Then, depending on the type of outcome and expected direction of the effect,
    implements the many-draw version of the certainty analysis function described above

    Results is a list of probabilities, ordered in the same order as the
    combinations fed in
    """

    ## get relevant info from tuple stored
    ## in list of all combos
    sample_size = one_combo[0]
    effect_size = one_combo[1]
    base_rate = one_combo[2]

    ## different outcomes or expected effect direction
    if type_of_outcome == "binary" and direction == "increase":

        results = degree_of_certainty_draws_perc(
            base_rate=base_rate,
            treatment_rate=base_rate + effect_size,
            num_participants=sample_size,
            num_draws=num_draws,
        )
    elif type_of_outcome == "binary" and direction == "decrease":

        results = degree_of_certainty_draws_perc(
            base_rate=base_rate,
            treatment_rate=base_rate - effect_size,
            num_participants=sample_size,
            num_draws=num_draws,
            tx_greater=False,
        )

    elif type_of_outcome == "count" and direction == "increase":

        results = degree_of_certainty_count_draws_perc(
            control_events_per_obs=base_rate,
            treatment_events_per_obs=base_rate + effect_size,
            control_exposure_per_obs=exposure,
            treatment_exposure_per_obs=exposure,
            num_participants=sample_size,
            num_draws=num_draws,
        )

    elif type_of_outcome == "count" and direction == "decrease":

        results = degree_of_certainty_count_draws_perc(
            control_events_per_obs=base_rate,
            treatment_events_per_obs=base_rate - effect_size,
            control_exposure_per_obs=exposure,
            treatment_exposure_per_obs=exposure,
            num_participants=sample_size,
            num_draws=num_draws,
            tx_greater=False,
        )

    return results
