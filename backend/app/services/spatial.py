"""WGS84 Geodesic Spatial Service for Farmland Boundary Management.
Implements genuine WGS84 ellipsoidal area calculation (authalic sphere / ellipsoidal excess),
polygon geometric validation (closure, vertex count, coordinates, self-intersection, duplicates),
and farmer declared area reconciliation.
"""

from typing import List, Tuple, Dict, Any, Union, Optional
import math
from datetime import datetime, timezone


# WGS84 Reference Ellipsoid Constants (EPSG:4326)
WGS84_SEMI_MAJOR = 6378137.0  # Semi-major axis (a) in metres
WGS84_FLATTENING = 1.0 / 298.257223563  # Flattening (f)
WGS84_SEMI_MINOR = WGS84_SEMI_MAJOR * (1.0 - WGS84_FLATTENING)  # Semi-minor axis (b) ~ 6356752.314245 m
WGS84_E2 = WGS84_FLATTENING * (2.0 - WGS84_FLATTENING)  # First eccentricity squared (e^2) ~ 0.00669437999014
WGS84_E = math.sqrt(WGS84_E2)  # Eccentricity (e)

# Conversion Constants
M2_PER_ACRE = 4046.8564224  # International acre in square metres
M2_PER_HECTARE = 10000.0  # Hectare in square metres


def _authalic_q(lat_rad: float) -> float:
    """Computes the authalic parameter q for a given latitude in radians on the WGS84 ellipsoid."""
    s = math.sin(lat_rad)
    e_s = WGS84_E * s
    # Guard against precision extremes near the poles
    if abs(s) >= 1.0:
        s = math.copysign(1.0, s)
        e_s = math.copysign(WGS84_E, s)
    term1 = s / (1.0 - WGS84_E2 * s * s)
    term2 = (1.0 / (2.0 * WGS84_E)) * math.log((1.0 - e_s) / (1.0 + e_s))
    return (1.0 - WGS84_E2) * (term1 - term2)


# Precompute WGS84 authalic radius (Rq) and q at the North Pole (qp)
_QP = _authalic_q(math.pi / 2.0)
WGS84_AUTHALIC_RADIUS = WGS84_SEMI_MAJOR * math.sqrt(_QP / 2.0)  # ~ 6371007.180918 m


def is_valid_wgs84(lat: float, lon: float, accuracy: Optional[float] = None) -> bool:
    """Checks if latitude and longitude are valid WGS84 coordinates.
    Optionally validates horizontal accuracy if provided.
    """
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
        return False
    if not (-90.0 <= lat <= 90.0):
        return False
    if not (-180.0 <= lon <= 180.0):
        return False
    if accuracy is not None:
        if not isinstance(accuracy, (int, float)) or math.isnan(accuracy) or math.isinf(accuracy):
            return False
        if accuracy <= 0.0 or accuracy > 100.0:
            return False
    return True


def segments_intersect(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> bool:
    """Determines if line segment (p1, p2) strictly intersects (p3, p4).
    Each point is (lat, lon).
    """
    def ccw(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    d1 = ccw(p1, p2, p3)
    d2 = ccw(p1, p2, p4)
    d3 = ccw(p3, p4, p1)
    d4 = ccw(p3, p4, p2)

    # Proper intersection: endpoints of one segment lie on opposite sides of the line through the other
    if ((d1 > 1e-12 and d2 < -1e-12) or (d1 < -1e-12 and d2 > 1e-12)) and \
       ((d3 > 1e-12 and d4 < -1e-12) or (d3 < -1e-12 and d4 > 1e-12)):
        return True

    return False


def validate_farm_polygon(
    vertices: Union[List[Tuple[float, float]], List[List[float]], List[Dict[str, Any]]],
) -> Tuple[bool, str]:
    """Validates farm boundary polygon:
    1. Must contain at least 3 distinct vertices.
    2. All points must be valid WGS84 coordinates.
    3. Consecutive duplicate coordinates are rejected.
    4. Duplicate interior/perimeter vertices are rejected.
    5. Edges must not self-intersect.
    6. Calculated WGS84 geodesic area must be non-zero and non-degenerate.
    """
    if not vertices or len(vertices) < 3:
        return False, "Polygon must have at least 3 vertices"

    # Normalize input into list of (lat, lon) floats
    raw_coords: List[Tuple[float, float]] = []
    for idx, v in enumerate(vertices):
        if isinstance(v, dict):
            lat = v.get("latitude") if "latitude" in v else v.get("lat")
            lon = v.get("longitude") if "longitude" in v else v.get("lon")
            if lat is None or lon is None:
                return False, f"Vertex at index {idx} missing latitude/longitude"
            acc = v.get("horizontal_accuracy") if "horizontal_accuracy" in v else v.get("accuracy")
            if acc is not None:
                try:
                    acc_f = float(acc)
                    if not is_valid_wgs84(float(lat), float(lon), accuracy=acc_f):
                        return False, f"Invalid horizontal accuracy at vertex {idx}: {acc_f}m (must be > 0.0 and <= 100.0m)"
                except (ValueError, TypeError):
                    return False, f"Invalid horizontal accuracy format at vertex {idx}"
            raw_coords.append((float(lat), float(lon)))
        elif hasattr(v, "latitude") and hasattr(v, "longitude"):
            lat = getattr(v, "latitude")
            lon = getattr(v, "longitude")
            if lat is None or lon is None:
                return False, f"Vertex at index {idx} missing latitude/longitude"
            acc = getattr(v, "horizontal_accuracy", getattr(v, "accuracy", None))
            if acc is not None:
                try:
                    acc_f = float(acc)
                    if not is_valid_wgs84(float(lat), float(lon), accuracy=acc_f):
                        return False, f"Invalid horizontal accuracy at vertex {idx}: {acc_f}m (must be > 0.0 and <= 100.0m)"
                except (ValueError, TypeError):
                    return False, f"Invalid horizontal accuracy format at vertex {idx}"
            raw_coords.append((float(lat), float(lon)))
        elif isinstance(v, (list, tuple)) and len(v) >= 2:
            raw_coords.append((float(v[0]), float(v[1])))
        else:
            return False, f"Invalid vertex format at index {idx}"

    # Check coordinate bounds
    for lat, lon in raw_coords:
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return False, f"Invalid WGS84 coordinate: ({lat}, {lon})"

    # Normalize closure: if last != first, close it
    is_closed = (
        abs(raw_coords[0][0] - raw_coords[-1][0]) < 1e-9 and
        abs(raw_coords[0][1] - raw_coords[-1][1]) < 1e-9
    )
    coords = list(raw_coords)
    if not is_closed:
        coords.append(coords[0])

    if len(coords) < 4:
        return False, "Closed polygon must have at least 4 coordinates (3 unique vertices)"

    # Distinct vertices check (excluding the closing duplicate)
    ring_vertices = coords[:-1]
    unique_vertices = set((round(pt[0], 9), round(pt[1], 9)) for pt in ring_vertices)
    if len(unique_vertices) < 3:
        return False, "Polygon must contain at least 3 distinct coordinates"

    # Check for consecutive duplicates (zero-length edges)
    for i in range(len(raw_coords) - 1):
        if abs(raw_coords[i][0] - raw_coords[i + 1][0]) < 1e-9 and \
           abs(raw_coords[i][1] - raw_coords[i + 1][1]) < 1e-9:
            return False, f"Duplicate consecutive vertex detected at index {i} and {i + 1}"

    # Check for duplicate non-consecutive vertices in polygon ring (pinch points / figure-8)
    # Applies to all polygons (whether pre-closed or unclosed)
    if len(unique_vertices) < len(ring_vertices):
        return False, "Duplicate non-consecutive vertex detected in polygon (pinch-point self-intersection)"

    # Self-intersection check across all non-adjacent edge pairs
    edges = [(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    num_edges = len(edges)

    for i in range(num_edges):
        for j in range(i + 1, num_edges):
            # Skip adjacent edges (including first and last edge sharing the origin vertex)
            if abs(i - j) <= 1 or (i == 0 and j == num_edges - 1):
                continue
            if segments_intersect(edges[i][0], edges[i][1], edges[j][0], edges[j][1]):
                return False, f"Polygon is self-intersecting between edges {i} and {j}"

    # Check planar degree Shoelace to detect collinear/degenerate sets of points
    planar_area = 0.0
    for i in range(len(coords) - 1):
        planar_area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
    if abs(planar_area) < 1e-8:
        return False, "Polygon has zero or degenerate area"

    # Geodesic area non-zero check (reject degenerate slivers under 0.1 m^2)
    area_m2 = calculate_wgs84_geodesic_area_sq_meters(coords)
    if area_m2 < 0.1:
        return False, "Polygon has zero or degenerate area"

    return True, "Valid polygon"


def calculate_wgs84_geodesic_area_sq_meters(
    vertices: Union[List[Tuple[float, float]], List[List[float]], List[Dict[str, Any]]],
) -> float:
    """Calculates genuine WGS84 ellipsoidal geodesic area in square metres (m^2).
    Uses the authalic sphere transformation where the authalic latitude beta
    maps the WGS84 ellipsoid surface isometrically into an equal-area sphere of radius Rq.
    Green's theorem for spherical polygon area is then integrated across all geodesic segments.
    """
    if not vertices or len(vertices) < 3:
        return 0.0

    raw_coords: List[Tuple[float, float]] = []
    for v in vertices:
        if isinstance(v, dict):
            lat = v.get("latitude") if "latitude" in v else v.get("lat")
            lon = v.get("longitude") if "longitude" in v else v.get("lon")
            if lat is not None and lon is not None:
                raw_coords.append((float(lat), float(lon)))
        elif isinstance(v, (list, tuple)) and len(v) >= 2:
            raw_coords.append((float(v[0]), float(v[1])))

    if len(raw_coords) < 3:
        return 0.0

    # Ensure closed polygon
    coords = list(raw_coords)
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    n = len(coords) - 1
    total = 0.0

    for i in range(n):
        lat1_rad = math.radians(coords[i][0])
        lon1_rad = math.radians(coords[i][1])
        lat2_rad = math.radians(coords[i + 1][0])
        lon2_rad = math.radians(coords[i + 1][1])

        # Longitude difference normalized to [-pi, pi] for antimeridian safety
        dlon = lon2_rad - lon1_rad
        dlon = (dlon + math.pi) % (2.0 * math.pi) - math.pi

        # Authalic sine latitudes
        sin_beta1 = _authalic_q(lat1_rad) / _QP
        sin_beta2 = _authalic_q(lat2_rad) / _QP

        # Trapezoidal authalic spherical integration
        total += dlon * (sin_beta1 + sin_beta2) / 2.0

    # Absolute area on the authalic sphere of radius Rq
    area_sq_meters = abs(total) * (WGS84_AUTHALIC_RADIUS ** 2)

    # Guard against complement hemisphere for extremely large spherical polygons
    authalic_hemisphere = 2.0 * math.pi * (WGS84_AUTHALIC_RADIUS ** 2)
    if area_sq_meters > authalic_hemisphere:
        area_sq_meters = 4.0 * math.pi * (WGS84_AUTHALIC_RADIUS ** 2) - area_sq_meters

    return float(area_sq_meters)


def calculate_farm_area_acres(
    vertices: Union[List[Tuple[float, float]], List[List[float]], List[Dict[str, Any]]],
) -> float:
    """Calculates farm parcel area in acres (1 acre = 4046.8564224 m^2)."""
    m2 = calculate_wgs84_geodesic_area_sq_meters(vertices)
    return float(m2 / M2_PER_ACRE)


def calculate_polygon_area_hectares(
    vertices: Union[List[Tuple[float, float]], List[List[float]], List[Dict[str, Any]]],
) -> float:
    """Calculates farm parcel area in hectares (1 ha = 10,000 m^2) using WGS84 geodesic area."""
    m2 = calculate_wgs84_geodesic_area_sq_meters(vertices)
    return float(round(m2 / M2_PER_HECTARE, 4))


# Alias for backward compatibility
calculate_farm_area_hectares = calculate_polygon_area_hectares


def validate_declared_area(
    calculated_sq_meters: float,
    declared_area: float,
    declared_unit: str = "acres",
    tolerance_pct: float = 30.0,
) -> Tuple[bool, str, Dict[str, Any]]:
    """Compares farmer-entered declared land area against WGS84 geodesic calculated area.
    Supported units: 'acres', 'hectares', 'sq_meters' / 'm2', 'guntas' (1 gunta = 101.17 m^2).
    """
    if declared_area <= 0.0:
        return False, "Declared area must be strictly positive", {
            "declared_area": declared_area,
            "declared_unit": declared_unit,
            "calculated_sq_meters": calculated_sq_meters,
            "tolerance_pct": tolerance_pct,
        }

    unit_lower = declared_unit.strip().lower()
    if unit_lower in ("acres", "acre"):
        declared_m2 = declared_area * M2_PER_ACRE
    elif unit_lower in ("hectares", "hectare", "ha"):
        declared_m2 = declared_area * M2_PER_HECTARE
    elif unit_lower in ("sq_meters", "m2", "sq_m", "sqm"):
        declared_m2 = declared_area
    elif unit_lower in ("guntas", "gunta"):
        declared_m2 = declared_area * 101.17141056
    else:
        declared_m2 = declared_area * M2_PER_ACRE  # default to acres

    diff_m2 = abs(calculated_sq_meters - declared_m2)
    pct_diff = (diff_m2 / declared_m2) * 100.0 if declared_m2 > 0 else 100.0

    is_within_tolerance = pct_diff <= tolerance_pct
    status_msg = (
        f"Declared area ({declared_area:.2f} {declared_unit}) matches geodesic area "
        f"within {tolerance_pct}% tolerance (difference: {pct_diff:.2f}%)"
        if is_within_tolerance
        else f"Discrepancy: Declared area ({declared_area:.2f} {declared_unit}) differs from "
             f"geodesic area ({calculated_sq_meters / M2_PER_ACRE:.2f} acres) by {pct_diff:.2f}% (exceeds {tolerance_pct}%)"
    )

    details = {
        "calculated_sq_meters": round(calculated_sq_meters, 2),
        "calculated_acres": round(calculated_sq_meters / M2_PER_ACRE, 4),
        "declared_area": declared_area,
        "declared_unit": declared_unit,
        "declared_sq_meters": round(declared_m2, 2),
        "percentage_difference": round(pct_diff, 2),
        "is_within_tolerance": is_within_tolerance,
        "tolerance_pct": tolerance_pct,
    }

    return is_within_tolerance, status_msg, details


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle geodesic distance between two WGS84 points in metres."""
    r = 6371000.0  # Earth mean radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return float(r * c)


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """Ray-casting algorithm to test whether point (lat, lon) is inside a polygon."""
    if not polygon or len(polygon) < 3:
        return False
    lat, lon = point
    n = len(polygon)
    inside = False

    p1_lat, p1_lon = polygon[0]
    for i in range(1, n + 1):
        p2_lat, p2_lon = polygon[i % n]
        if lon > min(p1_lon, p2_lon):
            if lon <= max(p1_lon, p2_lon):
                if lat <= max(p1_lat, p2_lat):
                    if p1_lon != p2_lon:
                        lat_inters = (lon - p1_lon) * (p2_lat - p1_lat) / (p2_lon - p1_lon) + p1_lat
                    else:
                        lat_inters = p1_lat
                    if p1_lat == p2_lat or lat <= lat_inters:
                        inside = not inside
        p1_lat, p1_lon = p2_lat, p2_lon

    return inside


def evaluate_altitude_plausibility(
    altitude: Optional[float],
    min_altitude: float = -100.0,
    max_altitude: float = 5000.0,
) -> Dict[str, Any]:
    """Validates altitude plausibility for agricultural evidence."""
    if altitude is None:
        return {"is_valid": True, "altitude": None, "note": "Altitude not recorded"}
    if not isinstance(altitude, (int, float)) or math.isnan(altitude) or math.isinf(altitude):
        return {"is_valid": False, "altitude": altitude, "note": "Non-finite altitude"}
    if altitude < min_altitude or altitude > max_altitude:
        return {
            "is_valid": False,
            "altitude": float(altitude),
            "note": f"Altitude {altitude}m out of terrestrial bounds [{min_altitude}m, {max_altitude}m]",
        }
    return {"is_valid": True, "altitude": float(altitude), "note": "Plausible altitude"}


def _parse_timestamp_seconds(val: Any) -> float:
    """Extracts timestamp as epoch seconds from ISO string, datetime, or number."""
    if isinstance(val, (int, float)):
        # If timestamp is in milliseconds (> 10^11), convert to seconds
        return float(val / 1000.0) if val > 1e11 else float(val)
    if isinstance(val, datetime):
        return val.timestamp()
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
        except Exception:
            return float(val)
    raise ValueError(f"Cannot parse timestamp from: {val}")


def validate_kinematic_transition(
    prev_coord: Dict[str, Any],
    curr_coord: Dict[str, Any],
    max_velocity_mps: float = 50.0,
) -> Dict[str, Any]:
    """Evaluates kinematic velocity, jump/teleportation, and altitude plausibility
    between sequential device location observations.
    
    Detects:
    - Zero time displacement (delta_t == 0 and distance > 10m -> teleportation)
    - Excessive velocity (> max_velocity_mps, default 50.0 m/s ~ 180 km/h)
    - Altitude out-of-bounds ([-100.0m, 5000.0m])
    """
    lat1 = float(prev_coord.get("latitude") if "latitude" in prev_coord else prev_coord["lat"])
    lon1 = float(prev_coord.get("longitude") if "longitude" in prev_coord else prev_coord["lon"])
    lat2 = float(curr_coord.get("latitude") if "latitude" in curr_coord else curr_coord["lat"])
    lon2 = float(curr_coord.get("longitude") if "longitude" in curr_coord else curr_coord["lon"])

    t1_raw = prev_coord.get("timestamp") or prev_coord.get("capture_timestamp") or prev_coord.get("time") or 0.0
    t2_raw = curr_coord.get("timestamp") or curr_coord.get("capture_timestamp") or curr_coord.get("time") or 0.0

    t1_sec = _parse_timestamp_seconds(t1_raw)
    t2_sec = _parse_timestamp_seconds(t2_raw)

    delta_t = abs(t2_sec - t1_sec)
    distance_m = haversine_distance_m(lat1, lon1, lat2, lon2)

    # Altitude check
    curr_alt = curr_coord.get("altitude") or curr_coord.get("alt") or curr_coord.get("elevation")
    alt_eval = evaluate_altitude_plausibility(float(curr_alt) if curr_alt is not None else None)

    if delta_t == 0.0:
        if distance_m > 10.0:
            return {
                "is_valid": False,
                "is_anomalous": True,
                "is_teleportation": True,
                "distance_meters": round(distance_m, 2),
                "delta_seconds": 0.0,
                "velocity_mps": float("inf"),
                "velocity_kmh": float("inf"),
                "altitude_plausibility": alt_eval,
                "reason": f"Displacement of {round(distance_m, 1)}m with zero elapsed time (teleportation)",
            }
        return {
            "is_valid": alt_eval["is_valid"],
            "is_anomalous": not alt_eval["is_valid"],
            "is_teleportation": False,
            "distance_meters": round(distance_m, 2),
            "delta_seconds": 0.0,
            "velocity_mps": 0.0,
            "velocity_kmh": 0.0,
            "altitude_plausibility": alt_eval,
            "reason": "Stationary identical observation",
        }

    velocity_mps = distance_m / delta_t
    is_speed_anomaly = velocity_mps > max_velocity_mps
    is_teleportation = is_speed_anomaly and distance_m > 50000.0

    is_anomalous = is_speed_anomaly or not alt_eval["is_valid"]
    reason = (
        f"Velocity {round(velocity_mps * 3.6, 1)} km/h exceeds maximum threshold {round(max_velocity_mps * 3.6, 1)} km/h"
        if is_speed_anomaly
        else (alt_eval["note"] if not alt_eval["is_valid"] else "Normal kinematic motion")
    )

    return {
        "is_valid": not is_anomalous,
        "is_anomalous": is_anomalous,
        "is_teleportation": is_teleportation,
        "distance_meters": round(distance_m, 2),
        "delta_seconds": round(delta_t, 2),
        "velocity_mps": round(velocity_mps, 2),
        "velocity_kmh": round(velocity_mps * 3.6, 2),
        "altitude_plausibility": alt_eval,
        "reason": reason,
    }


evaluate_kinematic_transition = validate_kinematic_transition


def check_mock_location(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Detects Android mock location and provider flags in device metadata."""
    flags = []
    if metadata.get("is_mock") is True or metadata.get("isMock") is True:
        flags.append("IS_MOCK_FLAG_SET")
    if metadata.get("mock_provider") is True or metadata.get("is_from_mock_provider") is True:
        flags.append("MOCK_PROVIDER_INDICATED")
    if str(metadata.get("provider", "")).lower() == "mock":
        flags.append("PROVIDER_NAME_MOCK")
    if metadata.get("mock_location") is True:
        flags.append("MOCK_LOCATION_FLAG")

    is_mock = len(flags) > 0
    return {
        "is_mock_detected": is_mock,
        "flags": flags,
        "reason": f"Mock location detected via flags: {', '.join(flags)}" if is_mock else "Genuine sensor hardware reported",
    }

