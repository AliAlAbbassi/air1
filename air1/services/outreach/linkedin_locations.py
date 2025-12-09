"""
LinkedIn Geo Region IDs mapping.

These IDs are used with the facetGeoRegion parameter when filtering company members by location.
Example URL: https://www.linkedin.com/company/murex/people/?facetGeoRegion=105606446

To find additional geo IDs:
1. Go to a company's people page on LinkedIn
2. Apply location filters
3. Check the URL for facetGeoRegion values
"""

# Middle East
LEBANON = "101834488"
PALESTINE = "106512162"
UAE = "104305776"
SAUDI_ARABIA = "100459316"
QATAR = "104690669"
KUWAIT = "104967344"
BAHRAIN = "106662619"
JORDAN = "105765362"
EGYPT = "106155005"
TURKEY = "102105699"

# Europe
FRANCE = "105015875"
UNITED_KINGDOM = "101165590"
GERMANY = "101282230"
NETHERLANDS = "102890719"
BELGIUM = "100565514"
SWITZERLAND = "106693272"
SPAIN = "105646813"
ITALY = "103350119"
PORTUGAL = "100364837"
IRELAND = "104738515"
AUSTRIA = "103883259"
POLAND = "105072130"
SWEDEN = "105117694"
NORWAY = "103819153"
DENMARK = "104514075"
FINLAND = "100456013"

# North America
UNITED_STATES = "103644278"
CANADA = "101174742"
MEXICO = "103323778"

# Asia Pacific
SINGAPORE = "102454443"
HONG_KONG = "102890883"
JAPAN = "101355337"
AUSTRALIA = "101452733"
INDIA = "102713980"
CHINA = "102890883"

# Cities (commonly used)
PARIS = "105606446"
LONDON = "102257491"
NEW_YORK = "102571732"
SAN_FRANCISCO = "102277331"
DUBAI = "104204107"
PLYMOUTH = "106178986"
BEIRUT = "105606446"
SINGAPORE_CITY = "102454443"

# Convenient groupings
MIDDLE_EAST = [LEBANON, UAE, SAUDI_ARABIA, QATAR, KUWAIT, BAHRAIN, JORDAN, EGYPT]
EUROPE = [
    FRANCE,
    UNITED_KINGDOM,
    GERMANY,
    NETHERLANDS,
    BELGIUM,
    SWITZERLAND,
    SPAIN,
    ITALY,
]
GCC = [UAE, SAUDI_ARABIA, QATAR, KUWAIT, BAHRAIN]
LEVANT = [LEBANON, JORDAN, SYRIA := "102683828", PALESTINE]


def get_location_ids(*names: str) -> list[str]:
    """
    Get location IDs by name.

    Args:
        *names: Location names (e.g., "LEBANON", "FRANCE", "PARIS")

    Returns:
        List of LinkedIn geo region IDs

    Example:
        >>> get_location_ids("LEBANON", "FRANCE")
        ['101834488', '105015875']
    """
    locations = globals()
    result = []
    for name in names:
        upper_name = name.upper().replace(" ", "_")
        if upper_name in locations:
            value = locations[upper_name]
            if isinstance(value, str):
                result.append(value)
            elif isinstance(value, list):
                result.extend(value)
    return result
