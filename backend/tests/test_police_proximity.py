import pytest
from api.v1.police_proximity import haversine_km, apply_privacy_jitter


def test_haversine_distance():
    # Distance between Bengaluru (12.9818, 77.5898) and Mysore (12.2958, 76.6394) is ~130 km
    d = haversine_km(12.9818, 77.5898, 12.2958, 76.6394)
    assert 120.0 <= d <= 145.0


def test_privacy_jitter_bounds():
    lat, lng = 12.9818, 77.5898
    seed = "test-case-uuid-1234"
    j_lat, j_lng = apply_privacy_jitter(lat, lng, seed)

    # Must be within ~0.0025 degrees (~275m)
    assert abs(j_lat - lat) <= 0.0026
    assert abs(j_lng - lng) <= 0.0026
    # Must be deterministic for the same seed
    j_lat2, j_lng2 = apply_privacy_jitter(lat, lng, seed)
    assert j_lat == j_lat2
    assert j_lng == j_lng2


def test_privacy_jitter_different_seeds():
    lat, lng = 12.9818, 77.5898
    j1_lat, j1_lng = apply_privacy_jitter(lat, lng, "case-alpha")
    j2_lat, j2_lng = apply_privacy_jitter(lat, lng, "case-beta")
    # Different seeds produce different offsets
    assert (j1_lat, j1_lng) != (j2_lat, j2_lng)
