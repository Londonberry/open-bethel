"""
Probability calibration for ranking systems that don't already emit
calibrated win probabilities.

Raw RPI's only "natural" probability transform is rpi_A / (rpi_A + rpi_B),
which is not calibrated — it systematically under- or over-confidently
predicts outcomes depending on RPI scale. That makes log-loss comparisons
against a Bradley-Terry-Ford system (which IS naturally calibrated)
structurally unfair: RPI's log-loss will look bad because of calibration,
not because of ranking quality.

This module fits a 2-parameter logistic

    P(A beats B) = 1 / (1 + exp(-(α + β · x)))

on a training split, where x is a caller-supplied feature (typically
log(rpi_A / rpi_B)). Fitting is Newton-Raphson on the binary-cross-entropy
objective; ~20 iterations is always enough for 2 parameters.

Calibrated predictions have the same rank order as the raw ones (β > 0),
so accuracy is unchanged — but log-loss becomes a fair comparison.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LogisticFit:
    """α + β·x logistic on a single scalar feature."""
    alpha: float
    beta: float
    iterations: int
    converged: bool

    def predict(self, x: float) -> float:
        z = self.alpha + self.beta * x
        # Guard against overflow for very confident predictions.
        if z > 30:
            return 1.0 - 1e-13
        if z < -30:
            return 1e-13
        return 1.0 / (1.0 + math.exp(-z))


def fit_logistic(
    xs: list[float],
    ys: list[int],
    *,
    max_iter: int = 100,
    tol: float = 1e-10,
) -> LogisticFit:
    """
    Fit a 2-parameter logistic by Newton-Raphson on binary cross-entropy.

    Parameters
    ----------
    xs : list of scalar features, one per training game.
    ys : list of 0/1 outcomes aligned with xs. y=1 means the "A team"
         (whichever side xs was computed from) won.

    Returns
    -------
    LogisticFit with α, β, iteration count, and convergence flag.

    Raises
    ------
    ValueError if xs and ys disagree in length or if the training set is
    empty.
    """
    if len(xs) != len(ys):
        raise ValueError(f"length mismatch: {len(xs)} features vs {len(ys)} labels")
    if not xs:
        raise ValueError("cannot fit logistic on empty training set")

    alpha = 0.0
    beta = 0.0
    for iteration in range(1, max_iter + 1):
        g0 = 0.0  # ∂L/∂α
        g1 = 0.0  # ∂L/∂β
        h00 = 0.0  # ∂²L/∂α²
        h01 = 0.0  # ∂²L/∂α∂β
        h11 = 0.0  # ∂²L/∂β²
        for x, y in zip(xs, ys):
            z = alpha + beta * x
            if z > 30:
                p = 1.0
            elif z < -30:
                p = 0.0
            else:
                p = 1.0 / (1.0 + math.exp(-z))
            g0 += y - p
            g1 += (y - p) * x
            w = p * (1.0 - p)
            h00 -= w
            h01 -= w * x
            h11 -= w * x * x

        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-18:
            # Near-singular Hessian — typically means the data are linearly
            # separable and β wants to run off to infinity. Bail with the
            # current iterate rather than produce NaNs.
            return LogisticFit(alpha, beta, iteration, converged=False)

        # θ_new = θ_old - H^(-1) · g
        da = -(h11 * g0 - h01 * g1) / det
        db = -(-h01 * g0 + h00 * g1) / det
        alpha += da
        beta += db
        if abs(da) + abs(db) < tol:
            return LogisticFit(alpha, beta, iteration, converged=True)

    return LogisticFit(alpha, beta, max_iter, converged=False)
