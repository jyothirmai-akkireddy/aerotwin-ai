"""Deterministic, bounded sensor noise generator for reproducible telemetry simulation."""

import numpy as np


class DeterministicNoiseGenerator:
    """Provides bounded Gaussian and uniform pseudo-random noise seeded deterministically."""

    def __init__(self, seed: int | None = 42):
        self._initial_seed = seed
        self._rng = np.random.RandomState(seed)

    def reset(self, seed: int | None = None) -> None:
        """Reset internal PRNG state to initial or new seed."""
        use_seed = seed if seed is not None else self._initial_seed
        self._rng = np.random.RandomState(use_seed)

    def gaussian(self, mean: float = 0.0, std: float = 1.0, bound_sigma: float = 3.5) -> float:
        """Generate bounded Gaussian noise clipped at +/- bound_sigma * std."""
        if std <= 0.0:
            return mean
        raw = self._rng.normal(loc=mean, scale=std)
        clipped = np.clip(raw, mean - (bound_sigma * std), mean + (bound_sigma * std))
        return float(clipped)

    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        """Generate uniform noise between low and high."""
        return float(self._rng.uniform(low=low, high=high))
