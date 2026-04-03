# world_bank_mapper.py
import requests
import re
import time

# In-memory cache to prevent spamming the World Bank API for identical ISO codes
wb_cache = {}

# NLP Text Fallback Dictionaries (Mapped to World Bank Income Groups)
# Useful if an API fails and returns 'UNKNOWN' for the ISO code, but the raw text
# says "Massachusetts General Hospital, Boston, USA".
FALLBACK_DICTIONARY = {
    # High Income (HIC) -> Parachute Risk
    'HIC': [
        'usa', 'united states', 'uk', 'united kingdom', 'england', 'scotland', 
        'wales', 'australia', 'canada', 'germany', 'france', 'italy', 'spain', 
        'netherlands', 'sweden', 'switzerland', 'belgium', 'austria', 'norway', 
        'denmark', 'finland', 'ireland', 'new zealand', 'singapore', 'japan', 
        'south korea', 'taiwan', 'israel', 'hong kong', 'saudi arabia', 'uae',
        'qatar'
    ],
    # Upper-Middle Income (UMIC) -> Global South
    'UMIC': [
        'china', 'brazil', 'mexico', 'russia', 'south africa', 'turkey', 
        'argentina', 'colombia', 'peru', 'thailand', 'malaysia', 'indonesia',
        'ecuador', 'chile'
    ],
    # Lower-Middle Income (LMIC) -> Global South
    'LMIC': [
        'india', 'pakistan', 'bangladesh', 'egypt', 'vietnam', 'philippines', 
        'nigeria', 'kenya', 'morocco', 'ukraine', 'iran'
    ],
    # Low Income (LIC) -> Global South
    'LIC': [
        'uganda', 'ethiopia', 'afghanistan', 'madagascar', 'mozambique', 'yemen',
        'syria', 'rwanda', 'sudan'
    ]
}

def get_world_bank_group(iso_code, affiliation_text=""):
    """
    Returns the World Bank Group (HIC, UMIC, LMIC, LIC) based strictly on ISO-2 code.
    If the ISO code is missing ('UNKNOWN' or None), implements a robust NLP fallback
    by searching the raw affiliation string for known country names.
    """
    iso_code = str(iso_code).strip().upper() if iso_code else "UNKNOWN"

    wb_group = "UNKNOWN"
    
    # 1. Official World Bank API Call (With Caching)
    if iso_code != "UNKNOWN" and len(iso_code) == 2:
        if iso_code in wb_cache:
            wb_group = wb_cache[iso_code]
        else:
            try:
                response = requests.get(f"https://api.worldbank.org/v2/country/{iso_code}?format=json", timeout=5)
                data = response.json()
                if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                    income_id = data[1][0].get('incomeLevel', {}).get('id')
                    if income_id == 'HIC': wb_group = 'HIC'
                    elif income_id == 'UMC': wb_group = 'UMIC'
                    elif income_id == 'LMC': wb_group = 'LMIC'
                    elif income_id == 'LIC': wb_group = 'LIC'
                
                wb_cache[iso_code] = wb_group
                time.sleep(0.1) # Be a good API citizen
            except Exception as e:
                pass # Silently fail and proceed to Text Fallback

    # 2. Text-Mining Fallback (If API or ISO failed)
    if wb_group == "UNKNOWN" and affiliation_text and affiliation_text != "UNKNOWN":
        affiliation_lower = str(affiliation_text).lower()
        # Clean punctuation to avoid 'usa.' missing 'usa'
        affiliation_clean = re.sub(r'[^\w\s]', ' ', affiliation_lower)
        words = affiliation_clean.split()

        found = False
        for group, countries in FALLBACK_DICTIONARY.items():
            for country in countries:
                # Need exact word match for short names like 'UK' 
                # or substring match for 'united states'
                if ' ' in country:
                    if country in affiliation_clean:
                        wb_group = group
                        found = True
                        break
                else:
                    if country in words:
                        wb_group = group
                        found = True
                        break
            if found:
                break

    return wb_group

def get_equity_classification(wb_group):
    """
    Translates the World Bank Group into the Narrative Review Equity Classes
    designed to highlight the Parachute Research dynamic.
    """
    if wb_group == 'HIC':
        return "HIC (High-Income / Parachute Risk)"
    elif wb_group in ['UMIC', 'LMIC', 'LIC']:
        return "Global South (Local Research)"
    else:
        return "UNKNOWN (Manual Review)"
