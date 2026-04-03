import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import os
import sys
from scipy.stats import norm
import warnings

warnings.filterwarnings('ignore')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from utils import (BASE_DIR, DATA_DIR, RESULTS_DIR, FIGURES_DIR, 
                   PROCESSING_DIR, CSV_PATH, setup_logging, log)

MATRIX_PATH = os.path.join(DATA_DIR, 'fleiss_kappa_matrix.csv')

def compute_fleiss_kappa(ratings_matrix, log_file):
    """Computes Fleiss' Kappa from a matrix of ratings."""
    N = ratings_matrix.shape[0]
    n = ratings_matrix.shape[1]

    categories = sorted(np.unique(ratings_matrix[~np.isnan(ratings_matrix)]).astype(int))
    k = len(categories)

    count_matrix = np.zeros((N, k))
    for i in range(N):
        for j, cat in enumerate(categories):
            count_matrix[i, j] = np.sum(ratings_matrix[i, :] == cat)

    row_sums = count_matrix.sum(axis=1)

    P_i = np.zeros(N)
    for i in range(N):
        ni = row_sums[i]
        if ni <= 1:
            P_i[i] = 0
        else:
            sum_sq = np.sum(count_matrix[i, :] ** 2)
            P_i[i] = (sum_sq - ni) / (ni * (ni - 1))

    P_bar = np.mean(P_i)
    total_ratings = np.sum(count_matrix)
    p_j = np.sum(count_matrix, axis=0) / total_ratings
    P_e = np.sum(p_j ** 2)

    if P_e == 1.0:
        kappa = 1.0
    else:
        kappa = (P_bar - P_e) / (1 - P_e)

    if kappa < 0:
        interpretation = 'Poor (worse than chance)'
    elif kappa < 0.20:
        interpretation = 'Slight'
    elif kappa < 0.40:
        interpretation = 'Fair'
    elif kappa < 0.60:
        interpretation = 'Moderate'
    elif kappa < 0.80:
        interpretation = 'Substantial'
    else:
        interpretation = 'Almost perfect'

    sum_p_j_cubed = np.sum(p_j ** 3)
    if (1 - P_e) != 0 and N * n * (n - 1) > 0:
        se_numerator = P_e - sum_p_j_cubed
        se_denominator = (1 - P_e) ** 2
        if se_denominator > 0 and se_numerator >= 0:
            se = np.sqrt(2 / (N * n * (n - 1))) * np.sqrt(se_numerator / se_denominator)
        else:
            se = 0.0
    else:
        se = 0.0

    ci_lower = max(-1.0, kappa - 1.96 * se)
    ci_upper = min(1.0, kappa + 1.96 * se)

    if se > 0:
        z_stat = kappa / se
        p_value = 2 * (1 - norm.cdf(abs(z_stat)))
    else:
        z_stat = np.inf if kappa > 0 else 0
        p_value = 0.0

    details = {
        'Fleiss_Kappa': kappa,
        'Interpretation': interpretation,
        'P_bar': P_bar,
        'P_e': P_e,
        'SE': se,
        'CI_95_Lower': ci_lower,
        'CI_95_Upper': ci_upper,
        'Z_statistic': z_stat,
        'p_value': p_value,
        'N_subjects': N,
        'n_raters': n,
        'k_categories': k,
        'Categories': str(categories)
    }

    return kappa, details


def generate_demo_data(log_file):
    """Generates simulated ratings for pipeline testing when actual matrix is missing."""
    np.random.seed(42)
    ground_truth = np.array([2, 5, 3, 4, 1, 3, 5, 2, 4, 3])
    n_papers = 10
    n_raters = 2

    ratings = np.zeros((n_papers, n_raters))
    for i in range(n_papers):
        for j in range(n_raters):
            noise_prob = 0.3 if ground_truth[i] in [1, 5] else 0.5
            if np.random.random() < noise_prob:
                noise = np.random.choice([-1, 0, 1])
            else:
                noise = 0
            score = max(1, min(5, ground_truth[i] + noise))
            ratings[i, j] = score

    return ratings


def generate_figure(ratings_matrix, kappa, details, is_demo, log_file):
    """Generates a heatmap representation of the ratings matrix with Kappa annotations."""
    fig, ax = plt.subplots(figsize=(12, 6))
    cax = ax.imshow(ratings_matrix, cmap='RdYlGn', aspect='auto', vmin=1, vmax=5, interpolation='nearest')

    for i in range(ratings_matrix.shape[0]):
        for j in range(ratings_matrix.shape[1]):
            val = int(ratings_matrix[i, j])
            text_color = 'white' if val in [1, 5] else 'black'
            ax.text(j, i, str(val), ha='center', va='center', fontsize=10, fontweight='bold', color=text_color)

    ax.set_xlabel('Reviewer', fontsize=12, fontweight='bold')
    ax.set_ylabel('Paper (Calibration Set)', fontsize=12, fontweight='bold')
    ax.set_xticks(range(ratings_matrix.shape[1]))
    ax.set_xticklabels([f'R{i+1}' for i in range(ratings_matrix.shape[1])], fontsize=9)
    ax.set_yticks(range(ratings_matrix.shape[0]))
    ax.set_yticklabels([f'P{i+1}' for i in range(ratings_matrix.shape[0])], fontsize=9)

    cbar = plt.colorbar(cax, ax=ax, shrink=0.8)
    cbar.set_label('LMIC Relevance Score', fontsize=11)
    cbar.set_ticks([1, 2, 3, 4, 5])
    cbar.set_ticklabels(['1 (Low)', '2', '3', '4', '5 (High)'])

    demo_tag = " [DEMO DATA]" if is_demo else ""
    ax.set_title(
        f"Inter-Rater Reliability Heatmap{demo_tag}\n"
        f"Fleiss' κ = {kappa:.4f} ({details['Interpretation']}) | "
        f"95% CI [{details['CI_95_Lower']:.3f}, {details['CI_95_Upper']:.3f}]",
        fontsize=13, fontweight='bold', pad=15
    )

    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, 'fleiss_kappa_heatmap.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return fig_path


def main():
    for d in [RESULTS_DIR, FIGURES_DIR, PROCESSING_DIR]:
        os.makedirs(d, exist_ok=True)

    try:
        log_file = setup_logging('module3_log.txt', "MODULE 3: Fleiss' Kappa — Inter-Rater Reliability")
        is_demo = not os.path.exists(MATRIX_PATH)

        if is_demo:
            log(log_file, "DEMO MODE: fleiss_kappa_matrix.csv not found. Using simulated data.")
            ratings_matrix = generate_demo_data(log_file)
        else:
            log(log_file, "REAL MODE: Loading consortium matrix.")
            matrix_df = pd.read_csv(MATRIX_PATH, encoding='utf-8')
            if matrix_df.columns[0].lower() in ['paper', 'paper_id', 'study', 'id', 'title']:
                matrix_df = matrix_df.iloc[:, 1:]
            ratings_matrix = matrix_df.values.astype(float)

        kappa, details = compute_fleiss_kappa(ratings_matrix, log_file)

        results_df = pd.DataFrame([details])
        results_path = os.path.join(RESULTS_DIR, 'module3_fleiss_kappa_results.csv')
        results_df.to_csv(results_path, index=False, encoding='utf-8')

        generate_figure(ratings_matrix, kappa, details, is_demo, log_file)

        log(log_file, f"MODULE 3 COMPLETED SUCCESSFULLY {'(DEMO)' if is_demo else '(REAL)'}")

    except Exception as e:
        log(log_file, f"ERROR: {str(e)}")
        import traceback
        log(log_file, traceback.format_exc())
        raise
    finally:
        log_file.close()

if __name__ == '__main__':
    main()
