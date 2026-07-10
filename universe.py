"""VRIDDHI वृद्धि — the stock universe.

A curated list of large, liquid NSE names as (symbol, display name, sector).
Start focused (these Nifty heavyweights) and grow the list over time — the
builder and app scale to whatever is here. Symbols are the NSE ticker WITHOUT
the ".NS" suffix (the builder appends it for Yahoo Finance).
"""

UNIVERSE: list[tuple[str, str, str]] = [
    # Energy
    ("RELIANCE", "Reliance Industries", "Energy"),
    ("ONGC", "Oil & Natural Gas Corp", "Energy"),
    ("NTPC", "NTPC Ltd", "Energy"),
    ("POWERGRID", "Power Grid Corp", "Energy"),

    # IT
    ("TCS", "Tata Consultancy Services", "IT"),
    ("INFY", "Infosys", "IT"),
    ("HCLTECH", "HCL Technologies", "IT"),
    ("WIPRO", "Wipro", "IT"),

    # Banking
    ("HDFCBANK", "HDFC Bank", "Banking"),
    ("ICICIBANK", "ICICI Bank", "Banking"),
    ("SBIN", "State Bank of India", "Banking"),
    ("KOTAKBANK", "Kotak Mahindra Bank", "Banking"),
    ("AXISBANK", "Axis Bank", "Banking"),

    # Auto
    ("TATAMOTORS", "Tata Motors", "Auto"),
    ("MARUTI", "Maruti Suzuki", "Auto"),
    ("M&M", "Mahindra & Mahindra", "Auto"),
    ("BAJAJ-AUTO", "Bajaj Auto", "Auto"),

    # FMCG
    ("ITC", "ITC Ltd", "FMCG"),
    ("HINDUNILVR", "Hindustan Unilever", "FMCG"),
    ("NESTLEIND", "Nestle India", "FMCG"),
    ("BRITANNIA", "Britannia Industries", "FMCG"),

    # Pharma
    ("SUNPHARMA", "Sun Pharmaceutical", "Pharma"),
    ("CIPLA", "Cipla", "Pharma"),
    ("DRREDDY", "Dr Reddy's Labs", "Pharma"),

    # Metals
    ("TATASTEEL", "Tata Steel", "Metals"),
    ("HINDALCO", "Hindalco Industries", "Metals"),
    ("JSWSTEEL", "JSW Steel", "Metals"),

    # Infra / Cement
    ("LT", "Larsen & Toubro", "Infrastructure"),
    ("ULTRACEMCO", "UltraTech Cement", "Cement"),
    ("GRASIM", "Grasim Industries", "Cement"),

    # Telecom
    ("BHARTIARTL", "Bharti Airtel", "Telecom"),
]
