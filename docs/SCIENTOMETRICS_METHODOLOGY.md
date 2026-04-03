# Scientometrics & Geographic Equity Methodology

## World Bank Data Integration
Fuente: World Bank Country Classification API
Endpoint: https://api.worldbank.org/v2/country/

Datos Extraídos:
- Country Code (ISO3)
- Income Group: LIC, LMIC, UMIC, HIC
- Region: EAP, ECA, LAC, MENA, SA, SSA
- Caching: 30 días en data/.cache/world_bank_countries.json

## Geographic Equity Analysis
Panel A: Income group distribution
- Cuenta de papers por income level
- Porcentaje de total
- Global North vs Global South classifications

Panel B: LMIC score by region
- Mediana LMIC score por región geográfica
- Aplicaciones dominantes por región

Panel C: Research gaps
- Heatmap countries × application areas
- Identifica brechas de investigación en geografías específicas
