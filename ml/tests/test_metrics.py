from __future__ import annotations

import numpy as np

from evaluate import confusion, ece, macro_f1, softmax, summarise, topk_accuracy


def test_topk_and_f1() -> None:
    probs = np.array([[0.7, 0.2, 0.1], [0.1, 0.3, 0.6], [0.5, 0.4, 0.1], [0.2, 0.2, 0.6]])
    y = np.array([0, 1, 1, 2])
    assert topk_accuracy(probs, y, 1) == 0.5
    assert topk_accuracy(probs, y, 2) == 1.0
    cm = confusion(y, probs.argmax(1), 3)
    assert cm.tolist() == [[1, 0, 0], [1, 0, 1], [0, 0, 1]]
    # F1 per class: 2/3, 0, 2/3
    assert abs(macro_f1(cm) - (4 / 9)) < 1e-9


def test_perfectly_calibrated_has_zero_ece() -> None:
    probs = np.array([[1.0, 0.0], [0.0, 1.0]])
    assert ece(probs, np.array([0, 1])) == 0.0
    assert ece(probs, np.array([1, 0])) == 1.0


def test_softmax_rows_sum_to_one() -> None:
    p = softmax(np.array([[1.0, 2.0, 3.0], [1000.0, 1000.0, 0.0]]))
    np.testing.assert_allclose(p.sum(axis=1), [1.0, 1.0])


def test_summary_handles_empty_subset() -> None:
    s = summarise(np.zeros((0, 2)), np.zeros(0, dtype=int), ["a", "b"])
    assert s["n"] == 0 and s["top1"] == 0.0
