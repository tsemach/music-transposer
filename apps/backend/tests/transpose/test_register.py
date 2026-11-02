from score_helpers import make_score

from backend.transpose.register import choose_interval


def test_auto_picks_same_sound_when_it_fits():
    chosen = choose_interval(make_score(["C5", "D5"]), "alto")

    assert (chosen.name, chosen.register, chosen.out_of_range) == ("P4", "same", 0)


def test_auto_picks_shifted_when_same_sound_goes_too_high():
    chosen = choose_interval(make_score(["D6"]), "alto")

    assert (chosen.name, chosen.register, chosen.out_of_range) == ("-P5", "shifted", 0)


def test_tie_goes_to_same_sound():
    chosen = choose_interval(make_score([]), "tenor")

    assert (chosen.name, chosen.register) == ("-P4", "same")


def test_both_out_of_range_picks_fewer_and_reports_count():
    chosen = choose_interval(make_score(["C3", "D6"]), "alto")

    assert (chosen.register, chosen.out_of_range) == ("shifted", 1)


def test_explicit_register_overrides_auto_but_reports_count():
    chosen = choose_interval(make_score(["C4", "D6"]), "alto", "same")

    assert (chosen.name, chosen.register, chosen.out_of_range) == ("P4", "same", 1)


def test_chord_pitches_all_counted():
    chosen = choose_interval(make_score(["D6 C3"]), "alto")

    assert (chosen.register, chosen.out_of_range) == ("shifted", 1)
