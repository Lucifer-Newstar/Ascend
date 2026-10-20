from __future__ import annotations

import numpy as np
from PIL import Image

from common import (
    CROP,
    IMAGENET_MEAN,
    IMAGENET_STD,
    average_hash,
    center_crop,
    preprocess,
    resize_short,
)


def test_shape_and_dtype() -> None:
    out = preprocess(Image.new("RGB", (640, 480), (120, 60, 30)))
    assert out.shape == (3, CROP, CROP)
    assert out.dtype == np.float32


def test_uniform_colour_normalises_per_channel() -> None:
    out = preprocess(Image.new("RGB", (300, 300), (255, 0, 128)))
    expected = (np.array([255, 0, 128], dtype=np.float32) / 255 - IMAGENET_MEAN) / IMAGENET_STD
    np.testing.assert_allclose(out[:, 100, 100], expected, rtol=1e-5)


def test_resize_keeps_aspect_and_crop_centres() -> None:
    img = resize_short(Image.new("RGB", (1000, 500)))
    assert img.size == (512, 256)
    assert center_crop(img).size == (CROP, CROP)


def test_shared_vector_is_stable() -> None:
    """The fixed gradient image below is the shared test vector: the sidecar asserts the
    same checksum, so a change on either side fails both test suites."""
    grad = np.zeros((256, 320, 3), dtype=np.uint8)
    grad[..., 0] = np.linspace(0, 255, 320, dtype=np.uint8)[None, :]
    grad[..., 1] = np.linspace(0, 255, 256, dtype=np.uint8)[:, None]
    grad[..., 2] = 90
    out = preprocess(Image.fromarray(grad))
    assert np.isfinite(out).all()
    assert abs(float(out.mean()) - VECTOR_MEAN) < 1e-4
    assert abs(float(out.std()) - VECTOR_STD) < 1e-4


def test_average_hash_ignores_resizing() -> None:
    img = Image.new("RGB", (200, 200), (0, 0, 0))
    img.paste((255, 255, 255), (0, 0, 100, 200))
    assert average_hash(img) == average_hash(img.resize((90, 90)))


# Recorded from the reference implementation (common.preprocess) on 2026-10-20.
VECTOR_MEAN = 0.0058505
VECTOR_STD = 0.8492255
