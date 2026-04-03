import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import sys

# Project root calculation: scripts/data_enrichment/world_bank/world_bank_fetcher.py -> root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Add scripts/data_enrichment to path so it can find world_bank.world_bank_mapper if needed, 
# but here they are in the same folder.
# We add the folder itself to sys.path to ensure 'import world_bank_mapper' works.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from world_bank_mapper import get_world_bank_group, get_equity_classification

# Load .env variables
load_dotenv(os.path.join(BASE_DIR, '.env'))
OPENALEX_MAIL = os.getenv('OPENALEX_MAIL', 'polite_pool@example.com')

# Paths
DATA_PATH = os.path.join(BASE_DIR, 'data', 'data-clean.csv')
RESULTS_DIR = os.path.join(BASE_DIR, 'tables')
OUTPUT_PATH = os.path.join(RESULTS_DIR, 'Author_Equity_Analysis.csv')

def get_doi_from_crossref(title):
    """
    Given a paper title, queries CrossRef to find its official DOI.
    """
    if not title or pd.isna(title):
        return None
        
    url = "https://api.crossref.org/works"
    params = {
        "query.bibliographic": str(title).strip(),
        "select": "DOI",
        "rows": 1
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        time.sleep(0.1) # Polite pool buffer
        if response.status_code == 200:
            data = response.json()
            items = data.get('message', {}).get('items', [])
            if items:
                return items[0].get('DOI')
    except Exception as e:
        pass
    return None

def extract_doi(raw_url, title):
    """
    Attempts to extract the DOI from a URL. If it fails,
    it queries CrossRef via the paper title to find the true DOI.
    """
    if not pd.isna(raw_url) and 'doi.org/' in str(raw_url).strip():
        return str(raw_url).strip().split('doi.org/')[-1]
        
    # Fallback to Crossref using the Title
    return get_doi_from_crossref(title)

def fetch_openalex_authors(doi):
    """
    Hits the OpenAlex API (using the Polite Pool via mailto) and extracts ALL authors:
    - Author (name, institution, country code, position, corresponding flag)
    """
    if not doi:
        return []
    
    headers = {"User-Agent": f"mailto:{OPENALEX_MAIL}"}
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # OpenAlex polite pool limit is 10 requests/second. 
        # A 0.2s sleep is safe.
        time.sleep(0.2) 
        
        if response.status_code != 200:
            return []
            
        data = response.json()
        authorships = data.get('authorships', [])
        
        all_authors = []
        
        for auth in authorships:
            # Safely extract core data
            author_obj = auth.get('author', {})
            author_name = author_obj.get('display_name', 'Unknown')
            
            # Extract affiliations
            institutions = auth.get('institutions', [])
            affiliations = " | ".join([inst.get('display_name') for inst in institutions if inst.get('display_name')])
            
            # Countries can be in institutions list
            countries = " | ".join(list(set([inst.get('country_code') for inst in institutions if inst.get('country_code')])))
            
            if not affiliations: affiliations = "Unknown"
            if not countries: countries = "UNKNOWN"
                
            entry = {
                'Name': author_name,
                'Affiliation': affiliations,
                'Country_ISO': countries,
                'Author_Position': auth.get('author_position', 'unknown'),
                'Is_Corresponding': auth.get('is_corresponding', False)
            }
            all_authors.append(entry)
            
        return all_authors
        
    except Exception as e:
        print(f"Error fetching {doi}: {e}")
        return []

def main():
    print("===================================================================")
    print("INITIALIZING SCIENTOMETRICS PIPELINE (PARACHUTE RESEARCH EXTRACTOR)")
    print("===================================================================")
    print(f"Loading data from: {DATA_PATH}")
    
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: Data file not found at {DATA_PATH}")
        return

    try:
        df = pd.read_csv(DATA_PATH, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(DATA_PATH, encoding='cp1252')
        
    print(f"Total Papers Found: {len(df)}")
    
    # We only care about papers with a valid title or URL
    # Map 'URL' if the csv has it under a different name
    if 'URL' not in df.columns:
        # Check if 'URL' is hidden or named differently (e.g. Paper_URL)
        pass

    df = df.dropna(subset=['Title'], how='all')
    print(f"Valid DOIs to process: {len(df)}")
    
    results = []
    
    # We use tqdm for a nice terminal progress bar
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Querying OpenAlex API"):
        study_id = row.get('Paper_ID', row.iloc[0])
        title = row.get('Title', 'Unknown')
        raw_url = row.get('URL', '')
        
        doi = extract_doi(raw_url, title)
        
        all_authors = []
        if doi:
            all_authors = fetch_openalex_authors(doi)
            
        if not all_authors:
            # Append a dummy author if extraction completely failed
            all_authors = [{
                'Name': 'API_FAILED',
                'Affiliation': 'UNKNOWN',
                'Country_ISO': 'UNKNOWN',
                'Author_Position': 'unknown',
                'Is_Corresponding': False
            }]
            
        for auth_data in all_authors:
            # --- WORLD BANK MAPPING & FALLBACK INVOCATION ---
            wb_group = get_world_bank_group(auth_data['Country_ISO'], auth_data['Affiliation'])
            equity = get_equity_classification(wb_group)
            
            # Append to Final Output Array
            results.append({
                'Study_ID': study_id,
                'Title': title,
                'DOI': doi if doi else "Not Found",
                
                'Author_Name': auth_data['Name'],
                'Author_Position': auth_data['Author_Position'],
                'Is_Corresponding': auth_data['Is_Corresponding'],
                
                'Affiliation': auth_data['Affiliation'],
                'Country_ISO': auth_data['Country_ISO'],
                'WorldBank_Group': wb_group,
                'Equity_Classification': equity
            })
        
    print("\nExtraction Complete! Compiling Supplement CSV...")
    
    # Save the parsed supplementary tracking table
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
    
    # Print Quick Analytical Summary to Terminal
    if 'WorldBank_Group' in out_df.columns:
        hic_authors = len(out_df[out_df['WorldBank_Group'] == 'HIC'])
        lmic_authors = len(out_df[out_df['WorldBank_Group'].isin(['UMIC', 'LMIC', 'LIC'])])
        
        print("===================================================================")
        print("PARACHUTE RESEARCH FAST SUMMARY (ALL AUTHORS):")
        print(f"Total Authors Processed: {len(out_df)}")
        print(f"Authors from HIC (High Income): {hic_authors}")
        print(f"Authors from Global South (UMIC/LMIC/LIC): {lmic_authors}")
        print(f"Result Saved To: {OUTPUT_PATH}")
        print("===================================================================")

if __name__ == '__main__':
    main()
