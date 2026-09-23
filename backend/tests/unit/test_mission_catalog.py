"""Unit tests for predefined reference missions catalog."""

from app.domain.mission.catalog import STANDARD_MISSIONS, get_predefined_mission


def test_predefined_missions_integrity():
    assert len(STANDARD_MISSIONS) == 5
    expected_ids = {
        "SURVEILLANCE_MISSION",
        "RAPID_CLIMB_HOT_DAY",
        "THROTTLE_DYNAMICS_BENCHMARK",
        "HIGH_ALTITUDE_FERRY",
        "EMERGENCY_DESCENT",
    }
    assert set(STANDARD_MISSIONS.keys()) == expected_ids

    for mission_id, mission in STANDARD_MISSIONS.items():
        assert mission.mission_id == mission_id
        assert mission.total_duration_sec > 0.0
        assert mission.phase_count > 0

        # Prototype integrity check: All reference missions must be explicitly labeled synthetic
        assert mission.is_synthetic is True, f"Mission {mission_id} missing is_synthetic=True"
        assert "SYNTHETIC / PROTOTYPE SCENARIO" in mission.description, (
            f"Mission {mission_id} missing required prototype disclaimer in description"
        )
        assert "SYNTHETIC / PROTOTYPE SCENARIO" in mission.name


def test_get_predefined_mission_lookup():
    # Case-insensitive resolution
    m1 = get_predefined_mission("surveillance_mission")
    assert m1 is not None
    assert m1.mission_id == "SURVEILLANCE_MISSION"

    m2 = get_predefined_mission("SURVEILLANCE_MISSION")
    assert m2 is not None
    assert m2.mission_id == "SURVEILLANCE_MISSION"

    m3 = get_predefined_mission("non_existent_mission")
    assert m3 is None
