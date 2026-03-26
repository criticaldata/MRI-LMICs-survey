"""
Abstract Numbers Reference
Prints the authoritative statistics for the abstract and manuscript.
Run this whenever the dataset changes to get the numbers to copy into the text.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

from mapper import load_data, get_project_root, N_PRIMARY_SR, N_ALL

def print_abstract_numbers():
    df = load_data()
    n = len(df)

    assert n == N_PRIMARY_SR, f"Data has {n} rows but N_PRIMARY_SR={N_PRIMARY_SR}"

    print(f"\n{'='*60}")
    print(f"ABSTRACT / MANUSCRIPT NUMBERS (n={n} primary SR studies)")
    print(f"(Note: {N_ALL} papers initially screened-in; {N_ALL - n} excluded)")
    print(f"{'='*60}\n")

    # Architecture
    cnn_n = (df['Architecture_Norm'] == 'CNN').sum()
    unet_n = (df['Architecture_Norm'] == 'U-Net').sum()
    print(f"Architecture:")
    print(f"  CNN:    {cnn_n}/{n} = {cnn_n/n*100:.1f}%")
    print(f"  U-Net:  {unet_n}/{n} = {unet_n/n*100:.1f}%")

    # Field strength / Low-field
    lf_n = (df['Low_Field_Norm'] == 'Yes').sum()
    print(f"\nLow-field mention: {lf_n}/{n} = {lf_n/n*100:.1f}%")

    # Application areas
    brain_n = (df['Application_Norm'] == 'Brain').sum()
    print(f"\nApplication areas:")
    print(f"  Brain: {brain_n}/{n} = {brain_n/n*100:.1f}%")
    for app, cnt in df['Application_Norm'].value_counts().items():
        print(f"  {app}: {cnt} ({cnt/n*100:.1f}%)")

    # LMIC scores
    high_lmic = (df['LMIC_Score'] >= 4).sum()
    print(f"\nLMIC relevance (Score 4-5): {high_lmic}/{n} = {high_lmic/n*100:.1f}%")
    print(f"Median LMIC score: {df['LMIC_Score'].median():.1f}")

    # Metrics reporting
    psnr_n = df['PSNR_Numeric'].notna().sum()
    ssim_n = df['SSIM_Numeric'].notna().sum()
    print(f"\nMetric reporting (of {n} studies):")
    print(f"  PSNR reported: {psnr_n} ({psnr_n/n*100:.1f}%) — NOT reported: {n-psnr_n} ({(n-psnr_n)/n*100:.1f}%)")
    print(f"  SSIM reported: {ssim_n} ({ssim_n/n*100:.1f}%) — NOT reported: {n-ssim_n} ({(n-ssim_n)/n*100:.1f}%)")
    if psnr_n > 0:
        print(f"  Median PSNR: {df['PSNR_Numeric'].median():.1f} dB")
    if ssim_n > 0:
        print(f"  Median SSIM: {df['SSIM_Numeric'].median():.3f}")

    # Clinical / Code
    clinical_n = (df['Clinical_Validation_Norm'] != 'None').sum()
    code_n = (df['Code_Available_Norm'] == 'Yes').sum()
    print(f"\nClinical validation: {clinical_n}/{n} = {clinical_n/n*100:.1f}%")
    print(f"Code available: {code_n}/{n} = {code_n/n*100:.1f}%")

    # Year range
    print(f"\nYear range: {int(df['Year'].min())}–{int(df['Year'].max())}")
    peak_year = df['Year'].value_counts().idxmax()
    peak_n = df['Year'].value_counts().max()
    print(f"Peak year: {peak_year} ({peak_n} papers, {peak_n/n*100:.1f}%)")

    print(f"\n{'='*60}")
    print("Copy these numbers into the abstract and manuscript text.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    print_abstract_numbers()
