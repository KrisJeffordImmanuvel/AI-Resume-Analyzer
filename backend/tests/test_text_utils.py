from text_utils import is_bullet, strip_bullet


def test_one_bullet_pattern_for_every_module():
    for line in ["- Built APIs", "* Built APIs", "• Built APIs", "1. Built APIs", "2) Built APIs", "  – Built APIs"]:
        assert is_bullet(line), line
        assert strip_bullet(line) == "Built APIs"
    for line in ["Built APIs", "2020 - 2022", "B.E. Computer Science", "-not a bullet", "3.5 years"]:
        assert not is_bullet(line), line
