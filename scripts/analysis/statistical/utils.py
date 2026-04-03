import os
import sys
import pandas as pd
from datetime import datetime

# Project root calculation: scripts/analysis/statistical/utils.py -> root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESULTS_DIR = os.path.join(BASE_DIR, 'tables')
FIGURES_DIR = os.path.join(BASE_DIR, 'figures')
PROCESSING_DIR = os.path.join(BASE_DIR, '06_processing_outputs')
CSV_PATH = os.path.join(DATA_DIR, 'data-clean.csv')

def setup_logging(log_filename, module_title):
    os.makedirs(PROCESSING_DIR, exist_ok=True)
    log_path = os.path.join(PROCESSING_DIR, log_filename)
    log_file = open(log_path, 'w', encoding='utf-8')
    log_file.write(f"{'='*70}\n{module_title}\n")
    log_file.write(f"Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_file.write(f"Python: {sys.version}\n{'='*70}\n\n")
    return log_file

def log(log_file, message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    formatted = f"[{timestamp}] {message}"
    safe_print = formatted.encode('ascii', errors='replace').decode('ascii')
    print(safe_print)
    log_file.write(formatted + '\n')
    log_file.flush()

def normalize_architecture(arch):
    if pd.isna(arch): return 'Other'
    arch_lower = str(arch).lower().strip()
    if 'gan' in arch_lower: return 'GAN'
    if 'transformer' in arch_lower: return 'Transformer'
    if 'u-net' in arch_lower or 'unet' in arch_lower: return 'U-Net'
    if 'hybrid' in arch_lower: return 'Hybrid'
    if 'cnn' in arch_lower or 'srcnn' in arch_lower or 'srdensenet' in arch_lower: return 'CNN'
    if 'diffusion' in arch_lower: return 'Diffusion'
    if 'dnn' in arch_lower: return 'DNN'
    return 'Other'

def normalize_dataset_type(dtype):
    if pd.isna(dtype): return 'Other'
    dtype_lower = str(dtype).lower().strip()
    if 'clinical' in dtype_lower: return 'Clinical'
    if 'synthetic' in dtype_lower or 'simulat' in dtype_lower: return 'Synthetic'
    if 'public' in dtype_lower or 'benchmark' in dtype_lower: return 'Public_Benchmark'
    if 'mixed' in dtype_lower: return 'Mixed'
    return 'Other'

def normalize_field_strength(field):
    if pd.isna(field): return 'Not_Specified'
    field_lower = str(field).lower().strip()
    if 'low' in field_lower: return 'Low_Field'
    if 'high' in field_lower: return 'High_Field'
    if 'mixed' in field_lower: return 'Mixed'
    if 'standard' in field_lower: return 'Standard_Field'
    return 'Not_Specified'

def normalize_clinical_validation(val):
    if pd.isna(val): return 'None'
    val_lower = str(val).lower().strip()
    if 'multi' in val_lower or 'reader' in val_lower: return 'Multi_Reader'
    if 'diagnostic' in val_lower or 'comparison' in val_lower: return 'Diagnostic_Comparison'
    if 'radiologist' in val_lower or 'visual' in val_lower: return 'Radiologist_Visual'
    if 'challenge' in val_lower or 'external' in val_lower: return 'External_Challenge'
    if 'prospective' in val_lower: return 'Prospective'
    if val_lower in ['none', 'n/a', 'na']: return 'None'
    return 'Other'

def normalize_code_available(val):
    if pd.isna(val): return 0
    return 1 if str(val).lower().strip() in ['yes', 'true', '1', 'upon_request'] else 0

def normalize_low_field_mentioned(val):
    if pd.isna(val): return 0
    return 1 if str(val).lower().strip() in ['yes', 'true', '1'] else 0

def has_metric_reported(val):
    if pd.isna(val): return 0
    val_str = str(val).lower().strip()
    if val_str in ['not reported', 'n/a', 'na', '', 'not reported.']: return 0
    return 1
