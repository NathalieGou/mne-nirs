import pandas as pd
from scipy import stats
import numpy as np
import re
from mne.utils import warn
import nilearn


def GLM_to_tidy_long(raw, statistic, design_matrix):
    """
    Exports GLM regression or contrast results in tidy format.

    Creates a long pandas data frame from regression results or contrast
    as computed by run_GLM or compute_contrast.

    Parameters
    ----------
    raw : MNE.Raw
        Instance of MNE raw.
    statistic : nilearn data,
        Either dict of nilearn.stats.regression.RegressionResults as returned
        by run_GLM, or nilearn.stats.contrasts.Contrast as returned by
        compute_contrast.
    design_matrix : DataFrame
        As specified in Nilearn

    Returns
    -------
    df : Tidy data frame,
        Data from statistic object in tidy data form.
    """

    if isinstance(statistic, dict):
        if isinstance(statistic[list(statistic.keys())[0]],
                      nilearn.stats.regression.RegressionResults):
            df = _tidy_RegressionResults(raw, statistic, design_matrix)

    elif isinstance(statistic, nilearn.stats.contrasts.Contrast):
        df = _tidy_Contrast(raw, statistic, design_matrix)

    else:
        warn("Unknown GLM result type")

    return df


def _tidy_Contrast(data, glm_est, design_matrix):
    df = pd.DataFrame()
    for idx, ch in enumerate(data.ch_names):
        df = df.append({'ch_name': ch,
                        'ContrastType': glm_est.contrast_type,
                        'variable': "effect",
                        'value': glm_est.effect[0][idx]},
                       ignore_index=True)
        df = df.append({'ch_name': ch,
                        'ContrastType': glm_est.contrast_type,
                        'variable': "p_value",
                        'value': glm_est.p_value()[idx]},
                       ignore_index=True)
        df = df.append({'ch_name': ch,
                        'ContrastType': glm_est.contrast_type,
                        'variable': "stat",
                        'value': glm_est.stat()[idx]},
                       ignore_index=True)
        df = df.append({'ch_name': ch,
                        'ContrastType': glm_est.contrast_type,
                        'variable': "z_score",
                        'value': glm_est.z_score()[idx]},
                       ignore_index=True)
    return df


def _tidy_RegressionResults(data, glm_est, design_matrix):

    if not (data.ch_names == list(glm_est.keys())):
        warn("MNE data structure does not match regression results")

    theta_estimates = np.zeros((len(glm_est), len(design_matrix.columns)))
    t_estimates = np.zeros((len(glm_est), len(design_matrix.columns)))
    df_estimates = np.zeros((len(glm_est), len(design_matrix.columns)))
    p_estimates = np.zeros((len(glm_est), len(design_matrix.columns)))
    mse_estimates = np.zeros((len(glm_est), len(design_matrix.columns)))

    for idx, name in enumerate(glm_est.keys()):
        theta_estimates[idx, :] = glm_est[name].theta.T
        df_estimates[idx, :] = glm_est[name].df_model
        mse_estimates[idx, :] = glm_est[name].MSE[0]
        for cond_idx, cond in enumerate(design_matrix.columns):
            t_estimates[idx, cond_idx] = glm_est[name].t(
                column=cond_idx)
            p_estimates[idx, cond_idx] = 2 * stats.t.cdf(
                -1.0 * np.abs(t_estimates[idx, cond_idx]),
                df=df_estimates[idx, cond_idx])

    df = pd.DataFrame()

    for ch_idx, ch in enumerate(data.ch_names):
        for cond_idx, cond in enumerate(design_matrix.columns):
            df = df.append({'ch_name': ch, 'condition': cond,
                            'variable': "theta",
                            'value': theta_estimates[ch_idx][cond_idx]},
                           ignore_index=True)
            df = df.append({'ch_name': ch, 'condition': cond,
                            'variable': "t",
                            'value': t_estimates[ch_idx][cond_idx]},
                           ignore_index=True)
            df = df.append({'ch_name': ch, 'condition': cond,
                            'variable': "df",
                            'value': df_estimates[ch_idx][cond_idx]},
                           ignore_index=True)
            df = df.append({'ch_name': ch, 'condition': cond,
                            'variable': "p_value",
                            'value': p_estimates[ch_idx][cond_idx]},
                           ignore_index=True)
            df = df.append({'ch_name': ch, 'condition': cond,
                            'variable': "mse",
                            'value': mse_estimates[ch_idx][cond_idx]},
                           ignore_index=True)

    return df


def _tidy_long_to_wide(d, expand_output=True):

    indices = ['ch_name']
    if 'condition' in d.columns:
        # Regression results have a column condition
        indices.append('condition')
    if 'ContrastType' in d.columns:
        # Regression results have a column condition
        indices.append('ContrastType')

    d = d.set_index(indices)
    d = d.pivot_table(columns='variable', values='value',
                      index=indices)
    d.reset_index(inplace=True)

    if expand_output:
        try:
            d["Source"] = [re.search(r'S(\d+)_D(\d+) (\w+)', ch).group(1)
                           for ch in d["ch_name"]]
            d["Detector"] = [re.search(r'S(\d+)_D(\d+) (\w+)', ch).group(2)
                             for ch in d["ch_name"]]
            d["Chroma"] = [re.search(r'S(\d+)_D(\d+) (\w+)', ch).group(3)
                           for ch in d["ch_name"]]
        except AttributeError:
            warn("Non standard source detector names used")
        d["Significant"] = d["p_value"] < 0.05

    return d
