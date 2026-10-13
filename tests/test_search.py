# Copyright 2026 ETH Zurich and the Alloy authors.
from collections.abc import Callable

from alloy.bench import search

WINNERS = {"r0": "w0", "r1": "w1"}
REFERENCES = {"r0": "ref0", "r1": "ref1"}


def judge(speedups: dict[tuple[str, ...], float]) -> tuple[Callable[[dict[str, str]], float], list[dict[str, str]]]:
    """A judge scoring each selection (as its region-ordered build names) from ``speedups``, and the calls it got."""
    calls: list[dict[str, str]] = []

    def score(selection: dict[str, str]) -> float:
        calls.append(selection)
        return speedups[tuple(selection[r] for r in sorted(selection))]

    return score, calls


def budget(scores: int) -> Callable[[], bool]:
    """Room for ``scores`` more judge scores."""
    left = [scores]

    def affordable() -> bool:
        left[0] -= 1
        return left[0] >= 0

    return affordable


def test_without_room_for_one_score_the_local_winners_go_unscored():
    score, calls = judge({})

    sut = search(WINNERS, REFERENCES, [("r0", ["a0"])], score, budget(0))

    assert sut == WINNERS
    assert calls == []


def test_a_faster_candidate_replaces_its_region_and_a_slower_one_does_not():
    score, calls = judge({("w0", "w1"): 1.5, ("a0", "w1"): 2.0, ("b0", "w1"): 1.8, ("a0", "a1"): 1.9})

    sut = search(WINNERS, REFERENCES, [("r0", ["a0", "b0"]), ("r1", ["a1"])], score, budget(10))

    assert sut == {"r0": "a0", "r1": "w1"}
    assert len(calls) == 4


def test_refused_local_winners_fall_back_to_the_references_and_any_correct_trial_beats_them():
    score, calls = judge({("w0", "w1"): -1.0, ("a0", "ref1"): 0.9})

    sut = search(WINNERS, REFERENCES, [("r0", ["a0"])], score, budget(10))

    assert sut == {"r0": "a0", "r1": "ref1"}
    assert calls == [WINNERS, {"r0": "a0", "r1": "ref1"}]


def test_the_search_stops_when_the_budget_runs_out_and_keeps_the_best_so_far():
    score, calls = judge({("w0", "w1"): 1.0, ("a0", "w1"): 1.2})

    sut = search(WINNERS, REFERENCES, [("r0", ["a0", "b0", "c0"])], score, budget(2))

    assert sut == {"r0": "a0", "r1": "w1"}
    assert len(calls) == 2


def test_the_build_already_chosen_for_a_region_is_not_scored_again():
    score, calls = judge({("w0", "w1"): 1.0, ("w0", "a1"): 0.5})
    same = {"r0": "w0", "r1": "w1"}

    sut = search(same, REFERENCES, [("r0", ["w0"]), ("r1", ["a1"])], score, budget(10))

    assert sut == same
    assert calls == [same, {"r0": "w0", "r1": "a1"}]
