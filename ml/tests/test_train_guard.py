from __future__ import annotations

import pytest

from common import TEST_OWN, Row
from train import OwnPhotoLeak, check_no_test_own


def row(split: str, tag: str = "") -> Row:
    return Row(
        path=f"images/{split}{tag}.png", label="idli", split=split, tag=tag, sha256="x", source=""
    )


def test_training_refuses_test_own_rows() -> None:
    with pytest.raises(OwnPhotoLeak, match="refusing to train"):
        check_no_test_own([row("train"), row("train", TEST_OWN)])
    with pytest.raises(OwnPhotoLeak):
        check_no_test_own([row("val", TEST_OWN)])


def test_test_own_in_test_is_fine() -> None:
    check_no_test_own([row("train"), row("val"), row("test", TEST_OWN)])
