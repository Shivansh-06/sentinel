# FATF (Financial Action Task Force) classifications as of 2024.
# Grey list = increased monitoring. Black list = call for action.
# This is a static snapshot — in production you'd sync this from
# https://www.fatf-gafi.org periodically.

FATF_BLACK_LIST = {
    "KP",  # North Korea
    "IR",  # Iran
    "MM",  # Myanmar
}

FATF_GREY_LIST = {
    "BF", "CM", "CD", "HT", "JM", "ML", "MZ",
    "NG", "PK", "PH", "SN", "SS", "SY", "TZ",
    "TT", "UG", "AE", "VN", "YE",
}

# Countries under broad international sanctions or elevated geopolitical risk
HIGH_RISK_COUNTRIES = {
    "RU",  # Russia — OFAC sectoral sanctions
    "BY",  # Belarus
    "CU",  # Cuba
    "VE",  # Venezuela
    "LY",  # Libya
    "SO",  # Somalia
    "SD",  # Sudan
    "ZW",  # Zimbabwe
}

# ISO 3166-1 alpha-2 to common name mapping for normalization
COUNTRY_NAME_TO_CODE = {
    "russia": "RU", "russian federation": "RU",
    "iran": "IR", "islamic republic of iran": "IR",
    "north korea": "KP", "democratic people's republic of korea": "KP",
    "china": "CN", "people's republic of china": "CN",
    "united states": "US", "usa": "US", "united states of america": "US",
    "united kingdom": "GB", "uk": "GB", "britain": "GB",
    "india": "IN",
    "pakistan": "PK",
    "ukraine": "UA",
    "belarus": "BY",
    "venezuela": "VE",
    "cuba": "CU",
    "myanmar": "MM", "burma": "MM",
    "syria": "SY", "syrian arab republic": "SY",
    "libya": "LY",
    "nigeria": "NG",
    "united arab emirates": "AE", "uae": "AE",
}


def normalize_country(country_input: str | None) -> str | None:
    """
    Converts country names to ISO codes for consistent risk lookup.
    Handles 'Russia', 'RU', 'russian federation' → 'RU'.
    """
    if not country_input:
        return None

    stripped = country_input.strip()

    if len(stripped) == 2:
        return stripped.upper()

    return COUNTRY_NAME_TO_CODE.get(stripped.lower())


def get_country_risk_score(country_input: str | None) -> tuple[float, str]:
    """
    Returns (score 0.0-1.0, risk_label).
    Higher score = higher risk.

    Returns both a numeric score for the composite calculation
    and a label for human-readable output in the case manager.
    """
    code = normalize_country(country_input)

    if code in FATF_BLACK_LIST:
        return 1.0, "blacklisted"
    if code in FATF_GREY_LIST:
        return 0.7, "grey_listed"
    if code in HIGH_RISK_COUNTRIES:
        return 0.6, "high_risk"
    if code is None:
        return 0.3, "unknown"
    return 0.1, "standard"