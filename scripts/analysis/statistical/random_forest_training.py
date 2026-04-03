import pandas as pd
import numpy as np

# Reproducibility
np.random.seed(42)
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import LeaveOneOut, cross_val_score, cross_val_predict
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
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
from utils import (normalize_architecture, normalize_dataset_type,
                   normalize_field_strength, normalize_clinical_validation,
                   normalize_code_available, normalize_low_field_mentioned,
                   has_metric_reported, BASE_DIR, DATA_DIR, RESULTS_DIR, 
                   FIGURES_DIR, PROCESSING_DIR, CSV_PATH, setup_logging, log)
from scripts.figures.mapper import LMIC_SCORE_MAP

RANDOM_SEED = 42

def load_and_filter_data(log_file):
    """Loads extraction CSV, drops invalid rows, and filters out non-primary studies."""
    df = pd.read_csv(CSV_PATH, encoding='utf-8')
    log(log_file, f"CSV loaded: {len(df)} total rows")

    first_col = df.columns[0]
    df = df.rename(columns={first_col: 'Study_ID'})
    df = df.dropna(subset=['Title'], how='all')
    df = df[df['Title'].notna() & (df['Title'].str.strip() != '')]

    df_clean = df.copy()

    # Map string labels to numeric before coercion
    df_clean['LMIC_Relevance_Score'] = df_clean['LMIC_Relevance_Score'].astype(str).map(LMIC_SCORE_MAP).fillna(df_clean['LMIC_Relevance_Score'])
    df_clean['LMIC_Relevance_Score'] = pd.to_numeric(df_clean['LMIC_Relevance_Score'], errors='coerce')
    df_clean = df_clean.dropna(subset=['LMIC_Relevance_Score'])
    df_clean = df_clean[(df_clean['LMIC_Relevance_Score'] >= 1) & (df_clean['LMIC_Relevance_Score'] <= 5)]
    log(log_file, f"Final filtered dataset size: {len(df_clean)}")

    return df_clean

def engineer_features(df, log_file):
    """Engineers binary dummy features for Random Forest processing."""
    X = pd.DataFrame()

    df['AI_Architecture_Clean'] = df['AI_Architecture'].apply(normalize_architecture)
    X['Is_CNN'] = (df['AI_Architecture_Clean'] == 'CNN').astype(int)
    X['Is_GAN'] = (df['AI_Architecture_Clean'] == 'GAN').astype(int)
    X['Is_UNet'] = (df['AI_Architecture_Clean'] == 'U-Net').astype(int)
    X['Is_Transformer'] = (df['AI_Architecture_Clean'] == 'Transformer').astype(int)

    df['Dataset_Type_Clean'] = df['Dataset_Type'].apply(normalize_dataset_type)
    X['Is_Clinical_Data'] = (df['Dataset_Type_Clean'] == 'Clinical').astype(int)

    X['Code_Available'] = df['Code_Available'].apply(normalize_code_available)

    df['Field_Strength_Clean'] = df['Field_Strength_Type'].apply(normalize_field_strength)
    X['Is_LowField_Hardware'] = (df['Field_Strength_Clean'].isin(['Low_Field', 'Mixed'])).astype(int)

    X['Low_Field_Mentioned'] = df['Low_Field_Mentioned'].apply(normalize_low_field_mentioned)

    df['Clinical_Validation_Clean'] = df['Clinical_Validation_Type'].apply(normalize_clinical_validation)
    X['Has_Clinical_Validation'] = (df['Clinical_Validation_Clean'] != 'None').astype(int)

    X['Has_PSNR'] = df['PSNR_Value'].apply(has_metric_reported)

    y = df['LMIC_Relevance_Score'].values
    feature_names = list(X.columns)

    return X, y, feature_names, None

def train_and_evaluate(X, y, feature_names, log_file):
    """Trains the Random Forest Regressor and retrieves feature importances."""
    X_np = X.values
    y_np = y

    model = RandomForestRegressor(
        n_estimators=500,
        max_depth=None,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
        n_jobs=None
    )

    loo = LeaveOneOut()
    cv_scores = cross_val_score(model, X_np, y_np, cv=loo, scoring='neg_mean_absolute_error')
    loo_mae = -cv_scores.mean()
    loo_mae_std = cv_scores.std()

    y_pred_loo = cross_val_predict(model, X_np, y_np, cv=loo)
    loo_r2 = r2_score(y_np, y_pred_loo)

    model.fit(X_np, y_np)
    importances = model.feature_importances_

    y_pred_train = model.predict(X_np)
    train_r2 = r2_score(y_np, y_pred_train)
    train_mae = mean_absolute_error(y_np, y_pred_train)
    train_rmse = np.sqrt(mean_squared_error(y_np, y_pred_train))

    metrics = {
        'LOO_CV_MAE': loo_mae,
        'LOO_CV_MAE_STD': loo_mae_std,
        'LOO_CV_R2': loo_r2,
        'Train_R2': train_r2,
        'Train_MAE': train_mae,
        'Train_RMSE': train_rmse,
        'n_samples': len(y_np),
        'n_features': len(feature_names),
        'n_estimators': 500
    }

    return model, importances, metrics

def save_results(importances, feature_names, metrics, log_file):
    """Saves analytical results to CSVs."""
    fi_df = pd.DataFrame({
        'Feature': feature_names,
        'Importance': importances,
        'Rank': np.argsort(-importances) + 1
    }).sort_values('Importance', ascending=False)

    fi_path = os.path.join(RESULTS_DIR, 'module1_feature_importance.csv')
    fi_df.to_csv(fi_path, index=False, encoding='utf-8')

    metrics_df = pd.DataFrame([metrics])
    metrics_path = os.path.join(RESULTS_DIR, 'module1_model_metrics.csv')
    metrics_df.to_csv(metrics_path, index=False, encoding='utf-8')

    return fi_df

def generate_figure(fi_df, metrics, log_file):
    """Generates the horizontal bar chart for Feature Importances."""
    fi_sorted = fi_df.sort_values('Importance', ascending=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.RdYlBu_r(np.linspace(0.2, 0.8, len(fi_sorted)))

    bars = ax.barh(
        range(len(fi_sorted)),
        fi_sorted['Importance'].values,
        color=colors,
        edgecolor='#333333',
        linewidth=0.5,
        height=0.6
    )

    labels = [name.replace('_', ' ') for name in fi_sorted['Feature'].values]
    ax.set_yticks(range(len(fi_sorted)))
    ax.set_yticklabels(labels, fontsize=11, fontweight='medium')

    for i, (val, _) in enumerate(zip(fi_sorted['Importance'].values, fi_sorted['Feature'].values)):
        ax.text(val + 0.005, i, f'{val:.3f}', va='center', fontsize=10, fontweight='bold', color='#333333')

    ax.set_xlabel('Feature Importance (Mean Decrease in Impurity)', fontsize=12, fontweight='bold')
    ax.set_title(f'Random Forest Feature Importance for LMIC Relevance Score\nMRI Super Resolution Narrative Review (n={metrics["n_samples"]} studies)',
                 fontsize=13, fontweight='bold', pad=15)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(0.5)
    ax.spines['bottom'].set_linewidth(0.5)
    ax.tick_params(axis='x', labelsize=10)
    ax.set_xlim(0, fi_sorted['Importance'].max() * 1.15)
    ax.axvline(x=0, color='#cccccc', linewidth=0.5)

    plt.tight_layout()
    fig_path = os.path.join(FIGURES_DIR, 'feature_importance.png')
    plt.savefig(fig_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    plt.close()

    return fig_path

def main():
    for d in [RESULTS_DIR, FIGURES_DIR, PROCESSING_DIR]:
        os.makedirs(d, exist_ok=True)

    try:
        log_file = setup_logging('module1_log.txt', 'MODULE 1: Random Forest Feature Importance')
        df_clean = load_and_filter_data(log_file)
        
        clean_path = os.path.join(PROCESSING_DIR, 'module1_cleaned_data.csv')
        df_clean.to_csv(clean_path, index=False, encoding='utf-8')

        X, y, feature_names, _ = engineer_features(df_clean, log_file)
        model, importances, metrics = train_and_evaluate(X, y, feature_names, log_file)
        fi_df = save_results(importances, feature_names, metrics, log_file)
        generate_figure(fi_df, metrics, log_file)

        log(log_file, "MODULE 1 COMPLETED SUCCESSFULLY")

    except Exception as e:
        log(log_file, f"ERROR: {str(e)}")
        import traceback
        log(log_file, traceback.format_exc())
        raise
    finally:
        log_file.close()

if __name__ == '__main__':
    main()
