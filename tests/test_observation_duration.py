"""Observation duration must depend on timestamps, not event metadata."""

import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boris import config as cfg
from boris import observation_operations


def media_observation(events, duration="10"):
    return {
        cfg.TYPE: cfg.MEDIA,
        cfg.FILE: {"1": ["clip.mp4"]},
        cfg.MEDIA_INFO: {cfg.LENGTH: {"clip.mp4": Decimal(duration)}},
        cfg.EVENTS: events,
    }


@pytest.mark.parametrize("duration, expected", [("5", "10"), ("10", "10"), ("20", "20")])
@pytest.mark.parametrize("reverse", [False, True])
def test_tied_event_times_do_not_compare_frame_indices(duration, expected, reverse):
    events = [
        [Decimal(10), "subject", "behavior", "", "", 42],
        [Decimal(10), "subject", "behavior", "", "", cfg.NA],
    ]
    if reverse:
        events.reverse()
    observation = media_observation(events, duration)
    before = deepcopy(observation)

    assert observation_operations.observation_total_length(observation) == Decimal(expected)
    assert observation == before


@pytest.mark.parametrize(
    "events, expected",
    [
        ([], "10"),
        ([[Decimal(4), "s", "b", "", "", 1]], "10"),
        ([[Decimal(12), "s", "b", "", "", 1]], "12"),
        (
            [
                [Decimal(12), "s", "b", "", "", 1],
                [Decimal(2), "s", "b", "", "", 2],
            ],
            "12",
        ),
    ],
)
def test_media_duration_preserves_event_and_media_bounds(events, expected):
    assert observation_operations.observation_total_length(media_observation(events)) == Decimal(expected)


def test_media_duration_uses_longest_queued_player():
    observation = media_observation([])
    observation[cfg.FILE] = {"1": ["clip.mp4", "second.mp4"], "2": ["other.mp4"], "3": []}
    observation[cfg.MEDIA_INFO][cfg.LENGTH].update({"second.mp4": Decimal(7), "other.mp4": Decimal(13)})

    assert observation_operations.observation_total_length(observation) == Decimal(17)


def test_missing_media_duration_retains_unavailable_result():
    observation = media_observation([[Decimal(12), "s", "b", "", "", 1]])
    observation[cfg.MEDIA_INFO][cfg.LENGTH] = {}

    assert observation_operations.observation_total_length(observation) == Decimal(-1)
