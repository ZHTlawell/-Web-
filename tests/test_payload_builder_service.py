"""Payload builder tests."""

from app.models.runzo import RunzoUserProfile
from app.services.payload_builder_service import build_simulate_payload


def _build_default_profile() -> RunzoUserProfile:
    """Build a default profile for tests."""
    return RunzoUserProfile()


def test_threshold_payload_structure_is_correct():
    """Threshold should generate warmup/main/rest structure."""
    daily = {
        "trainingType": "Threshold",
        "runningDistance": 8,
        "trainingBlocks": [
            {"minPace": "6:00", "maxPace": "6:30", "distance": 2},
            {"minPace": "4:30", "maxPace": "4:45", "distance": 4},
        ],
    }

    payload = build_simulate_payload(daily, _build_default_profile())

    assert payload["trainingPlan"]["trainingType"] == "Threshold"
    assert payload["trainingPlan"]["phasePace"]["warmup"]["min"] == "6:00"
    assert payload["trainingPlan"]["phasePace"]["main"]["max"] == "4:45"
    assert payload["trainingPlan"]["phaseDistance"]["main"] == 4.0


def test_interval_payload_keeps_training_blocks():
    """Interval should keep trainingBlocks intact."""
    daily = {
        "trainingType": "Interval",
        "runningDistance": 5,
        "trainingBlocks": [
            {
                "distance": 0.5,
                "minPace": "7:20",
                "maxPace": "7:50",
            },
            {
                "repeatNum": 3,
                "intervalDistance": 0.8,
                "intervalMinPace": "5:10",
                "intervalMaxPace": "5:40",
                "joggingDistance": 0.2,
                "joggingMinPace": "7:20",
                "joggingMaxPace": "7:50",
            },
        ],
    }

    payload = build_simulate_payload(daily, _build_default_profile())

    assert payload["trainingPlan"]["trainingType"] == "Interval"
    assert payload["trainingPlan"]["trainingBlocks"][1]["repeatNum"] == 3
    assert payload["trainingPlan"]["trainingBlocks"][1]["intervalDistance"] == 0.8


def test_rest_payload_reuses_easy_logic():
    """Rest should reuse the Easy-like payload structure."""
    daily = {
        "trainingType": "Rest",
        "runningDistance": 3,
        "trainingBlocks": [{"minPace": "7:00", "maxPace": "7:30"}],
    }

    payload = build_simulate_payload(daily, _build_default_profile())

    assert payload["trainingPlan"]["trainingType"] == "Rest"
    assert payload["trainingPlan"]["phasePace"]["main"]["min"] == "7:00"
