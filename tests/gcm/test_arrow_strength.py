import random

import networkx as nx
import numpy as np
import pandas as pd
import pytest
from flaky import flaky
from pytest import approx
from scipy import stats

from dowhy.gcm import ClassifierFCM, AdditiveNoiseModel, ProbabilisticCausalModel, fit, arrow_strength, \
    ScipyDistribution
from dowhy.gcm.divergence import estimate_kl_divergence_continuous
from dowhy.gcm.influence import arrow_strength_of_model
from dowhy.gcm.ml import create_logistic_regression_classifier, create_linear_regressor


@pytest.fixture
def preserve_random_generator_state():
    numpy_state = np.random.get_state()
    random_state = random.getstate()
    yield
    np.random.set_state(numpy_state)
    random.setstate(random_state)


@flaky(max_runs=5)
def test_given_kl_divergence_attribution_func_when_estimate_arrow_strength_then_returns_expected_results():
    causal_model = ProbabilisticCausalModel(nx.DiGraph([('X1', 'X2'), ('X0', 'X2')]))
    causal_model.set_causal_mechanism('X1', ScipyDistribution(stats.norm, loc=0, scale=1))
    causal_model.set_causal_mechanism('X0', ScipyDistribution(stats.norm, loc=0, scale=1))
    causal_model.set_causal_mechanism('X2', AdditiveNoiseModel(prediction_model=create_linear_regressor()))

    X0 = np.random.normal(0, 1, 1000)
    X1 = np.random.normal(0, 1, 1000)

    test_data = pd.DataFrame({'X0': X0,
                              'X1': X1,
                              'X2': 3 * X0 + X1 + np.random.normal(0, 0.2, X0.shape[0])})
    fit(causal_model, test_data)

    causal_strengths = arrow_strength(causal_model,
                                      'X2',
                                      difference_estimation_func=estimate_kl_divergence_continuous)
    assert causal_strengths[('X0', 'X2')] == approx(2.76, abs=0.4)
    assert causal_strengths[('X1', 'X2')] == approx(1.6, abs=0.4)


@flaky(max_runs=5)
def test_given_continuous_data_with_default_atttribution_func_when_estimate_arrow_strength_then_returns_expected_results():
    causal_model = ProbabilisticCausalModel(nx.DiGraph([('X1', 'X2'), ('X0', 'X2')]))
    causal_model.set_causal_mechanism('X1', ScipyDistribution(stats.norm, loc=0, scale=1))
    causal_model.set_causal_mechanism('X0', ScipyDistribution(stats.norm, loc=0, scale=1))
    causal_model.set_causal_mechanism('X2', AdditiveNoiseModel(
        prediction_model=create_linear_regressor()))

    X0 = np.random.normal(0, 1, 1000)
    X1 = np.random.normal(0, 1, 1000)

    test_data = pd.DataFrame({'X0': X0,
                              'X1': X1,
                              'X2': 3 * X0 + X1 + np.random.normal(0, 0.2, X0.shape[0])})
    fit(causal_model, test_data)

    causal_strengths = arrow_strength(causal_model, 'X2', tolerance=10 ** -4)
    assert causal_strengths[('X0', 'X2')] == approx(9, abs=0.5)
    assert causal_strengths[('X1', 'X2')] == approx(1, abs=0.2)


@flaky(max_runs=5)
def test_arrow_strength_with_squared_mean_difference():
    causal_model = ProbabilisticCausalModel(nx.DiGraph([('X1', 'X2'), ('X0', 'X2')]))
    causal_model.set_causal_mechanism('X1', ScipyDistribution(stats.norm, loc=0, scale=1))
    causal_model.set_causal_mechanism('X0', ScipyDistribution(stats.norm, loc=0, scale=1))
    causal_model.set_causal_mechanism('X2', AdditiveNoiseModel(prediction_model=create_linear_regressor()))

    X0 = np.random.normal(0, 1, 1000)
    X1 = np.random.normal(0, 1, 1000)

    test_data = pd.DataFrame({'X0': X0,
                              'X1': X1,
                              'X2': 2 * X0 + X1 + np.random.normal(0, 0.2, X0.shape[0])})
    fit(causal_model, test_data)

    causal_strengths \
        = arrow_strength(causal_model, 'X2', tolerance=10 ** -5,
                         difference_estimation_func=lambda x, y:
                         (np.mean(x).squeeze() - np.mean(y).squeeze()) ** 2)
    assert causal_strengths[('X0', 'X2')] == approx(4, abs=0.4)
    assert causal_strengths[('X1', 'X2')] == approx(1, abs=0.4)

    causal_strengths \
        = arrow_strength(causal_model, 'X2', tolerance=10 ** -5,
                         difference_estimation_func=lambda x, y:
                         (np.mean(x).squeeze() - np.mean(y).squeeze()) ** 2)
    assert causal_strengths[('X0', 'X2')] == approx(4, abs=0.4)
    assert causal_strengths[('X1', 'X2')] == approx(1, abs=0.4)


@flaky(max_runs=5)
def test_arrow_strength_of_model_classifier():
    X = np.random.random((1000, 5))
    Y = []

    for n in X:
        if (n[0] + n[1] + np.random.random(1)) > 1.5:
            Y.append(0)
        else:
            Y.append(1)

    classifier_sem = ClassifierFCM(create_logistic_regression_classifier())
    classifier_sem.fit(X, np.array(Y).astype(str))

    assert arrow_strength_of_model(classifier_sem, X) == approx(np.array([0.3, 0.3, 0, 0, 0]), abs=0.1)
