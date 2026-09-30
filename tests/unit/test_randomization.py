"""Radius randomization tests covering determinism and bounds."""

from __future__ import annotations

from geo.geodesy import haversine_distance_m
from geo.models import GeoCircle, GeoCoordinate, RandomizationScope
from geo.randomization import derive_seed, randomization_report, sample_verified, seed_for_scope

CIRCLE = GeoCircle(center=GeoCoordinate(52.52, 13.405, accuracy_m=5000), radius_m=5000)


def test_same_seed_produces_identical_coordinate():
    first, _ = sample_verified(CIRCLE, 12345)
    second, _ = sample_verified(CIRCLE, 12345)
    assert first == second


def test_different_seeds_produce_different_coordinates():
    first, _ = sample_verified(CIRCLE, 1)
    second, _ = sample_verified(CIRCLE, 2)
    assert first != second


def test_sample_stays_inside_radius_for_many_seeds():
    for seed in range(200):
        coordinate, distance = sample_verified(CIRCLE, seed)
        assert distance <= CIRCLE.radius_m
        assert haversine_distance_m(CIRCLE.center, coordinate) <= CIRCLE.radius_m


def test_zero_radius_returns_center():
    circle = GeoCircle(center=GeoCoordinate(52.52, 13.405), radius_m=0)
    coordinate, distance = sample_verified(circle, 7)
    assert coordinate == circle.center
    assert distance == 0


def test_seed_scope_semantics():
    per_query_a, note_a = seed_for_scope(RandomizationScope.PER_QUERY, 7, "session-a", "profile-a", 0)
    per_query_b, _ = seed_for_scope(RandomizationScope.PER_QUERY, 7, "session-a", "profile-a", 1)
    per_session_a, note_session = seed_for_scope(RandomizationScope.PER_SESSION, 7, "session-a", "profile-a", 0)
    per_session_b, _ = seed_for_scope(RandomizationScope.PER_SESSION, 7, "session-a", "profile-a", 9)
    assert per_query_a != per_query_b
    assert per_session_a == per_session_b
    assert note_a == "per-query-seeded"
    assert note_session == "per-session-stable"


def test_derive_seed_is_stable_across_processes():
    assert derive_seed("a", "b") == derive_seed("a", "b")
    assert derive_seed("a", "b") != derive_seed("b", "a")


def test_distribution_report_is_within_radius_and_centered():
    report = randomization_report(CIRCLE, RandomizationScope.PER_QUERY, 99, sample_count=512)
    assert report["max_within_radius"] is True
    assert report["max_distance_m"] <= CIRCLE.radius_m
    assert abs(report["mean_distance_m"] - report["expected_mean_distance_m"]) < CIRCLE.radius_m * 0.1
