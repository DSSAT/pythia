def euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the euclidean distance between two lat/lon points.

    Designed for fast comparisons (e.g., finding the closest point in a list).
    Smaller values indicate closer proximity, but the output is NOT in any standard
    unit (km, miles, etc.) and should not be used for actual distance calculations.

    Args:
        lat1, lon1: Latitude/longitude of the first point (decimal degrees).
        lat2, lon2: Latitude/longitude of the second point (decimal degrees).

    Returns:
        A non-negative float representing relative 'distance' (dimensionless).
        Only meaningful for comparing proximity between points.
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    return (lat1 - lat2)**2 + (lon1 - lon2)**2
