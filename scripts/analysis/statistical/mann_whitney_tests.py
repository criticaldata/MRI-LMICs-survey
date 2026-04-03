import pandas as pd
import numpy as np

# Reproducibility
np.random.seed(42)
from scipy.stats import mannwhitneyu, chi2_contingency, fisher_exact
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import os
import sys
import warnings

warnings.filterwarnings('ignore')

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from utils import (has_metric_reported, normalize_code_available, 
                   normalize_low_field_mentioned, normalize_field_strength, 
                   normalize_dataset_type, BASE_DIR, DATA_DIR, RESULTS_DIR, 
                   FIGURES_DIR, PROCESSING_DIR, CSV_PATH, setup_logging, log)


def load_and_prepare(log_file):
    """Loads CSV extraction file and filters data similarly to Module 1."""
    df = pd.read_csv(CSV_PATH, encoding='utf-8')
    first_col = df.columns[0]
    df = df.rename(columns={first_col: 'Study_ID'})
    df = df.dropna(subset=['Title'], how='all')
    df = df[df['Title'].notna() & (df['Title'].str.strip() != '')]

    review_mask = (
        df['Primary_Focus'].fillna('').str.lower().str.contains('survey|review') |
        df['Notes_Questions'].fillna('').str.lower().str.contains('is a review|review - include') |
        df['MRI_Application_Area'].fillna('').str.lower().str.contains('not mri|n/a')
    )
    df = df[~review_mask].copy()

    df['Reports_PSNR'] = df['PSNR_Value'].apply(has_metric_reported)
    df['Reports_SSIM'] = df['SSIM_Value'].apply(has_metric_reported)
    df['Reports_Any_Metric'] = ((df['Reports_PSNR'] == 1) | (df['Reports_SSIM'] == 1)).astype(int)

    df['LMIC_Relevance_Score'] = pd.to_numeric(df['LMIC_Relevance_Score'], errors='coerce')
    df['Code_Binary'] = df['Code_Available'].apply(normalize_code_available)
    df['LowField_Binary'] = df['Low_Field_Mentioned'].apply(normalize_low_field_mentioned)
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

    return df


def run_mann_whitney(df, log_file):
    """Runs Mann-Whitney U test comparing reporters vs. non-reporters for continuous/ordinal variables."""
    group_a = df[df['Reports_PSNR'] == 1]
    group_b = df[df['Reports_PSNR'] == 0]

    results = []

    score_a = group_a['LMIC_Relevance_Score'].dropna()
    score_b = group_b['LMIC_Relevance_Score'].dropna()

    if len(score_a) > 0 and len(score_b) > 0:
        stat, p_val = mannwhitneyu(score_a, score_b, alternative='two-sided')
        n1, n2 = len(score_a), len(score_b)
        effect_size = 1 - (2 * stat) / (n1 * n2)
        results.append({
            'Variable': 'LMIC_Relevance_Score',
            'Group_A_n': n1,
            'Group_A_median': score_a.median(),
            'Group_A_mean': score_a.mean(),
            'Group_A_std': score_a.std(),
            'Group_B_n': n2,
            'Group_B_median': score_b.median(),
            'Group_B_mean': score_b.mean(),
            'Group_B_std': score_b.std(),
            'U_statistic': stat,
            'p_value': p_val,
            'Effect_Size_r': effect_size,
            'Significant': 'Yes' if p_val < 0.05 else 'No'
        })

    year_a = group_a['Year'].dropna()
    year_b = group_b['Year'].dropna()

    if len(year_a) > 0 and len(year_b) > 0:
        stat, p_val = mannwhitneyu(year_a, year_b, alternative='two-sided')
        n1, n2 = len(year_a), len(year_b)
        effect_size = 1 - (2 * stat) / (n1 * n2)
        results.append({
            'Variable': 'Publication_Year',
            'Group_A_n': n1,
            'Group_A_median': year_a.median(),
            'Group_A_mean': year_a.mean(),
            'Group_A_std': year_a.std(),
            'Group_B_n': n2,
            'Group_B_median': year_b.median(),
            'Group_B_mean': year_b.mean(),
            'Group_B_std': year_b.std(),
            'U_statistic': stat,
            'p_value': p_val,
            'Effect_Size_r': effect_size,
            'Significant': 'Yes' if p_val < 0.05 else 'No'
        })

    return pd.DataFrame(results)


def run_chi_square(df, log_file):
    """Runs Chi-Square / Fisher Exact Test for categorical differences."""
    results = []
    categorical_vars = [
        ('Code_Binary', 'Code_Available'),
        ('LowField_Binary', 'Low_Field_Mentioned'),
    ]

    for col, label in categorical_vars:
        contingency = pd.crosstab(df[col], df['Reports_PSNR'])
        chi2, p_chi, dof, expected = chi2_contingency(contingency, correction=True)
        min_expected = expected.min()

        if min_expected < 5 and contingency.shape == (2, 2):
            odds_ratio, p_fisher = fisher_exact(contingency)
            results.append({
                'Variable': label, 'Test': 'Fisher_Exact', 'Statistic': odds_ratio,
                'p_value': p_fisher, 'Min_Expected_Cell': min_expected,
                'Significant': 'Yes' if p_fisher < 0.05 else 'No', 'Note': f'OR={odds_ratio:.2f}'
            })
        else:
            results.append({
                'Variable': label, 'Test': 'Chi_Square', 'Statistic': chi2,
                'p_value': p_chi, 'Min_Expected_Cell': min_expected,
                'Significant': 'Yes' if p_chi < 0.05 else 'No', 'Note': f'χ²={chi2:.2f}, df={dof}'
            })

    return pd.DataFrame(results)


def run_sensitivity_analysis(df, log_file):
    """Runs sensitivity checks for sub-categories vs reporting rates."""
    results = []

    lf_report = df.groupby('LowField_Binary')['Reports_PSNR'].mean()
    results.append({
        'Analysis': 'LowField_vs_PSNR_Report',
        'Test': 'Proportion_Comparison',
        'Statistic': lf_report.to_dict(),
        'p_value': None,
        'Interpretation': f'Low-field report rate: {lf_report.get(1, 0):.1%} vs Standard: {lf_report.get(0, 0):.1%}'
    })

    code_report = df.groupby('Code_Binary')['Reports_PSNR'].mean()
    results.append({
        'Analysis': 'Code_vs_PSNR_Report',
        'Test': 'Proportion_Comparison',
        'Statistic': code_report.to_dict(),
        'p_value': None,
        'Interpretation': f'With code report rate: {code_report.get(1, 0):.1%} vs Without: {code_report.get(0, 0):.1%}'
    })

    return pd.DataFrame(results)


def generate_figure(df, mw_results, log_file):
    """Generates the 2x2 bias analysis composition figure."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Reporting Bias Analysis: PSNR Reporters vs Non-Reporters\n'
                 'MRI Super Resolution Narrative Review',
                 fontsize=14, fontweight='bold', y=0.98)

    group_a = df[df['Reports_PSNR'] == 1]
    group_b = df[df['Reports_PSNR'] == 0]

    color_a = '#2196F3'
    color_b = '#FF5722'

    # Panel A: Box plot LMIC Score
    ax = axes[0, 0]
    data_a = group_a['LMIC_Relevance_Score'].dropna().values
    data_b = group_b['LMIC_Relevance_Score'].dropna().values

    bp = ax.boxplot([data_a, data_b], positions=[1, 2], widths=0.5,
                    patch_artist=True, medianprops=dict(color='black', linewidth=2))
    bp['boxes'][0].set_facecolor(color_a)
    bp['boxes'][0].set_alpha(0.7)
    bp['boxes'][1].set_facecolor(color_b)
    bp['boxes'][1].set_alpha(0.7)

    ax.set_xticklabels([f'Reports PSNR\n(n={len(data_a)})', f'No PSNR\n(n={len(data_b)})'], fontsize=10)
    ax.set_ylabel('LMIC Relevance Score', fontsize=11)
    ax.set_title('(A) LMIC Score Distribution', fontsize=12, fontweight='bold')

    if len(mw_results) > 0:
        p_val = mw_results[mw_results['Variable'] == 'LMIC_Relevance_Score']['p_value'].values
        if len(p_val) > 0:
            significance = '***' if p_val[0] < 0.001 else '**' if p_val[0] < 0.01 else '*' if p_val[0] < 0.05 else 'ns'
            ax.text(1.5, ax.get_ylim()[1] * 0.95, f'p = {p_val[0]:.4f} ({significance})',
                   ha='center', fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.set_ylim(0, 6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Panel B: Code Available by Group
    ax = axes[0, 1]
    code_data = pd.DataFrame({
        'Reports PSNR': [group_a['Code_Binary'].sum(), len(group_a) - group_a['Code_Binary'].sum()],
        'No PSNR': [group_b['Code_Binary'].sum(), len(group_b) - group_b['Code_Binary'].sum()]
    }, index=['Code Available', 'No Code'])

    code_pct = code_data.div(code_data.sum()) * 100
    code_pct.T.plot(kind='bar', stacked=True, ax=ax, color=['#4CAF50', '#E0E0E0'],
                    edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Percentage (%)', fontsize=11)
    ax.set_title('(B) Code Availability', fontsize=12, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontsize=10)
    ax.legend(fontsize=9, loc='upper right')
    ax.set_ylim(0, 110)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Panel C: Field Strength Category
    ax = axes[1, 0]
    df_temp = df.copy()
    df_temp['Field_Cat'] = df_temp['Field_Strength_Type'].apply(lambda x: normalize_field_strength(x).replace('_', ' '))

    field_counts = pd.crosstab(df_temp['Field_Cat'], df_temp['Reports_PSNR'])
    field_counts.columns = ['No PSNR', 'Reports PSNR']
    field_counts.plot(kind='bar', ax=ax, color=[color_b, color_a], edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Number of Studies', fontsize=11)
    ax.set_title('(C) Field Strength Distribution', fontsize=12, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    ax.legend(fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Panel D: Dataset Type Category
    ax = axes[1, 1]
    df_temp['Dataset_Cat'] = df_temp['Dataset_Type'].apply(lambda x: normalize_dataset_type(x).replace('_', ' '))

    dataset_counts = pd.crosstab(df_temp['Dataset_Cat'], df_temp['Reports_PSNR'])
    dataset_counts.columns = ['No PSNR', 'Reports PSNR']
    dataset_counts.plot(kind='bar', ax=ax, color=[color_b, color_a], edgecolor='black', linewidth=0.5)
    ax.set_ylabel('Number of Studies', fontsize=11)
    ax.set_title('(D) Dataset Type Distribution', fontsize=12, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha='right', fontsize=9)
    ax.legend(fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig_path = os.path.join(FIGURES_DIR, 'bias_analysis.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()
    
    return fig_path


def save_group_profiles(df, log_file):
    """Compiles descriptive auditing profiles for the Reporter vs Non-Reporter splits."""
    group_a = df[df['Reports_PSNR'] == 1]
    group_b = df[df['Reports_PSNR'] == 0]

    profile = {
        'Metric': [
            'n', 'LMIC_Score_mean', 'LMIC_Score_median', 'LMIC_Score_std',
            'Code_Available_%', 'Low_Field_%', 'Year_mean', 'Year_median',
            'Reports_SSIM_%', 'Clinical_Validation_%'
        ],
        'Group_A_Reports_PSNR': [
            len(group_a), group_a['LMIC_Relevance_Score'].mean(), group_a['LMIC_Relevance_Score'].median(), group_a['LMIC_Relevance_Score'].std(),
            group_a['Code_Binary'].mean() * 100, group_a['LowField_Binary'].mean() * 100, group_a['Year'].mean(), group_a['Year'].median(),
            group_a['Reports_SSIM'].mean() * 100, (group_a['Clinical_Validation_Type'].fillna('None').str.lower() != 'none').mean() * 100
        ],
        'Group_B_No_PSNR': [
            len(group_b), group_b['LMIC_Relevance_Score'].mean(), group_b['LMIC_Relevance_Score'].median(), group_b['LMIC_Relevance_Score'].std(),
            group_b['Code_Binary'].mean() * 100, group_b['LowField_Binary'].mean() * 100, group_b['Year'].mean(), group_b['Year'].median(),
            group_b['Reports_SSIM'].mean() * 100, (group_b['Clinical_Validation_Type'].fillna('None').str.lower() != 'none').mean() * 100
        ]
    }

    profile_df = pd.DataFrame(profile)
    profile_path = os.path.join(PROCESSING_DIR, 'module2_group_profiles.csv')
    profile_df.to_csv(profile_path, index=False, encoding='utf-8')

    return profile_df


def main():
    for d in [RESULTS_DIR, FIGURES_DIR, PROCESSING_DIR]:
        os.makedirs(d, exist_ok=True)

    try:
        log_file = setup_logging('module2_log.txt', 'MODULE 2: Mann-Whitney U Test (Report Bias Analysis)')
        df = load_and_prepare(log_file)

        mw_results = run_mann_whitney(df, log_file)
        mw_path = os.path.join(RESULTS_DIR, 'module2_mann_whitney_results.csv')
        mw_results.to_csv(mw_path, index=False, encoding='utf-8')

        chi_results = run_chi_square(df, log_file)
        chi_path = os.path.join(RESULTS_DIR, 'module2_chi_square_results.csv')
        chi_results.to_csv(chi_path, index=False, encoding='utf-8')

        sens_results = run_sensitivity_analysis(df, log_file)
        sens_path = os.path.join(RESULTS_DIR, 'module2_sensitivity_analysis.csv')
        sens_results.to_csv(sens_path, index=False, encoding='utf-8')

        save_group_profiles(df, log_file)
        generate_figure(df, mw_results, log_file)

        log(log_file, "MODULE 2 COMPLETED SUCCESSFULLY")

    except Exception as e:
        log(log_file, f"ERROR: {str(e)}")
        import traceback
        log(log_file, traceback.format_exc())
        raise
    finally:
        log_file.close()

if __name__ == '__main__':
    main()
