"""Deterministic, world-consistent value noise (no dependency on chunk boundaries)."""
from __future__ import annotations

import numpy as np


def _hash(ix: np.ndarray, iy: np.ndarray, seed: int) -> np.ndarray:
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def value_noise(ox: int, oy: int, w: int, h: int, scale: float, seed: int) -> np.ndarray:
    """Smooth noise in [0,1] for the tile window (ox..ox+w, oy..oy+h)."""
    xs = (np.arange(w) + ox) / scale
    ys = (np.arange(h) + oy) / scale
    X, Y = np.meshgrid(xs, ys)
    ix, iy = np.floor(X).astype(np.int64), np.floor(Y).astype(np.int64)
    fx, fy = X - ix, Y - iy
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)
    a = _hash(ix, iy, seed)
    b = _hash(ix + 1, iy, seed)
    c = _hash(ix, iy + 1, seed)
    d = _hash(ix + 1, iy + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(ox: int, oy: int, w: int, h: int, scale: float, seed: int, octaves: int = 3) -> np.ndarray:
    total = np.zeros((h, w))
    amp, norm, s = 1.0, 0.0, scale
    for o in range(octaves):
        total += amp * value_noise(ox, oy, w, h, s, seed + o * 7919)
        norm += amp
        amp *= 0.5
        s /= 2.0
    return total / norm


def white(ox: int, oy: int, w: int, h: int, seed: int) -> np.ndarray:
    """Per-tile uniform random in [0,1), stable per world tile."""
    X, Y = np.meshgrid(np.arange(w) + ox, np.arange(h) + oy)
    return _hash(X, Y, seed)
