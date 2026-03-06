"""
Seal movement model following McConnell, Smout & Wu (2017):
- Empirical Inter‑Haulout Transition Rate (I‑HTR) simulator (Markov transitions among haulout clusters)
- Mechanistic IBM layer with haulout/at‑sea states, energy budget, and habitat‑biased movement

References:
  McConnell, Smout & Wu (2017) "Modelling Harbour Seal Movements" (Scottish Marine & Freshwater Science Vol 8 No 20).
  Data + report portal: https://data.marine.gov.scot/dataset/modelling-harbour-seal-movements
  (Replace synthetic placeholders below with parameters/data estimated from your telemetry and environment)
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError as _exc:
    raise ImportError(
        "numpy is required for the seal movement model. "
        "Install it with: micromamba install -n shiny numpy"
    ) from _exc

try:
    import pandas as pd
except ImportError as _exc:
    raise ImportError(
        "pandas is required for the seal movement model. "
        "Install it with: micromamba install -n shiny pandas"
    ) from _exc

# -----------------------------
# Utility helpers
# -----------------------------

def normalize_rows(M: np.ndarray) -> np.ndarray:
    """Normalize rows to sum to 1 (handling zero rows)."""
    M = np.array(M, dtype=float)
    rowsums = M.sum(axis=1, keepdims=True)
    rowsums[rowsums == 0] = 1.0
    return np.asarray(M / rowsums)  # type: ignore[no-any-return]

def softmax(x: np.ndarray, tau: float = 1.0) -> np.ndarray:
    """Temperature-scaled softmax for site choice utilities."""
    x = np.array(x, dtype=float)
    x = x - np.max(x)  # numerical stability
    ex = np.exp(x / max(1e-9, tau))
    s = ex.sum()
    return np.asarray(ex / s if s > 0 else np.ones_like(x) / len(x))  # type: ignore[no-any-return]

def reflect_into_bounds(xy: np.ndarray, bounds: tuple[float, float, float, float]) -> np.ndarray:
    """Reflect a point at rectangular boundaries (xmin, xmax, ymin, ymax)."""
    xmin, xmax, ymin, ymax = bounds
    x, y = float(xy[0]), float(xy[1])
    if x < xmin:
        x = xmin + (xmin - x)
    if x > xmax:
        x = xmax - (x - xmax)
    if y < ymin:
        y = ymin + (ymin - y)
    if y > ymax:
        y = ymax - (y - ymax)
    return np.array([x, y], dtype=float)  # type: ignore[no-any-return]

def gradient_field(raster: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute a simple gradient field of the habitat raster (central differences)."""
    gy, gx = np.gradient(raster)  # note: numpy returns [grad_y, grad_x]
    return gx, gy

# -----------------------------
# I‑HTR model (empirical)
# -----------------------------

@dataclass
class IHTRConfig:
    P: np.ndarray               # transition matrix (KxK), rows sum to 1
    n_agents: int = 100
    T: int = 24 * 30            # number of time steps, e.g., hourly for ~1 month
    initial_dist: np.ndarray | None = None  # initial distribution across K clusters

def simulate_IHTR(cfg: IHTRConfig, random_state: int | None = None) -> pd.DataFrame:
    """
    Simulate agent transitions among haulout clusters using a time-homogeneous transition matrix.
    Returns a long data frame with columns: t, agent, cluster

    Vectorized implementation: transitions are computed per-state-group rather than
    per-agent, giving O(T*K) random draws instead of O(T*n_agents).
    """
    rng = np.random.default_rng(seed=random_state)
    P = normalize_rows(cfg.P)
    K = P.shape[0]

    # Initial states
    if cfg.initial_dist is None:
        init_probs = np.ones(K) / K
    else:
        init_probs = np.array(cfg.initial_dist, dtype=float)
        init_probs = init_probs / init_probs.sum()

    states = rng.choice(K, size=cfg.n_agents, p=init_probs)

    # Pre-allocate output arrays (vectorized recording)
    n_records = cfg.T * cfg.n_agents
    t_col: np.ndarray = np.repeat(np.arange(cfg.T), cfg.n_agents)
    agent_col: np.ndarray = np.tile(np.arange(cfg.n_agents), cfg.T)
    cluster_col: np.ndarray = np.empty(n_records, dtype=np.int32)

    for t in range(cfg.T):
        # Record current states (vectorized)
        start_idx = t * cfg.n_agents
        cluster_col[start_idx : start_idx + cfg.n_agents] = states

        # Vectorized transitions: process all agents in each state together
        new_states = np.empty_like(states)
        for k in range(K):
            mask = states == k
            count = mask.sum()
            if count > 0:
                # Sample next states for all agents currently in state k
                new_states[mask] = rng.choice(K, size=count, p=P[k])
        states = new_states

    df = pd.DataFrame({"t": t_col, "agent": agent_col, "cluster": cluster_col})
    return df

# -----------------------------
# Mechanistic IBM (process-based)
# -----------------------------

@dataclass
class Environment:
    bounds: tuple[float, float, float, float]  # (xmin, xmax, ymin, ymax)
    habitat: np.ndarray  # 2D raster (Ny x Nx), higher is better habitat
    cellsize: float = 1.0
    haulout_sites: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))  # array of (x, y)
    site_quality: np.ndarray | None = None  # optional per-site preference (utility offset)

    def habitat_value(self, xy: np.ndarray) -> float:
        """Bilinear sample of habitat raster at continuous xy."""
        x, y = xy
        xmin, xmax, ymin, ymax = self.bounds
        # map to raster indices
        Nx = self.habitat.shape[1]
        Ny = self.habitat.shape[0]
        # normalize to [0, Nx-1] and [0, Ny-1]
        u = (x - xmin) / max(1e-9, (xmax - xmin)) * (Nx - 1)
        v = (y - ymin) / max(1e-9, (ymax - ymin)) * (Ny - 1)
        if u < 0 or u > Nx - 1 or v < 0 or v > Ny - 1:
            return 0.0

        u0 = int(np.floor(u))
        v0 = int(np.floor(v))
        u1 = min(u0 + 1, Nx - 1)
        v1 = min(v0 + 1, Ny - 1)
        du = u - u0
        dv = v - v0

        # bilinear interpolation
        val = ((1 - du) * (1 - dv) * self.habitat[v0, u0] +
               du * (1 - dv) * self.habitat[v0, u1] +
               (1 - du) * dv * self.habitat[v1, u0] +
               du * dv * self.habitat[v1, u1])
        return float(val)

    def gradient(self, xy: np.ndarray) -> np.ndarray:
        """Approximate gradient at xy using precomputed gradients."""
        if not hasattr(self, "_gx") or not hasattr(self, "_gy"):
            self._gx, self._gy = gradient_field(self.habitat)

        x, y = xy
        xmin, xmax, ymin, ymax = self.bounds
        Nx = self.habitat.shape[1]
        Ny = self.habitat.shape[0]
        u = (x - xmin) / max(1e-9, (xmax - xmin)) * (Nx - 1)
        v = (y - ymin) / max(1e-9, (ymax - ymin)) * (Ny - 1)

        u = np.clip(u, 0, Nx - 1)
        v = np.clip(v, 0, Ny - 1)
        u0 = int(np.floor(u))
        v0 = int(np.floor(v))
        return np.asarray([self._gx[v0, u0], self._gy[v0, u0]], dtype=float)  # type: ignore[no-any-return]

@dataclass
class IBMParams:
    dt_h: float = 1.0  # time step in hours
    speed_max: float = 2.0  # max displacement per step (grid units) ~ coarse proxy for swim speed
    diffusive_sigma: float = 0.8  # random movement component (grid units)
    bias_strength: float = 1.2  # scales movement bias toward habitat gradient
    metabolic_cost: float = 0.04  # energy cost per hour at sea
    foraging_gain_scale: float = 0.06  # gain multiplier * habitat_value
    haulout_recovery: float = 0.15  # energy recovery per hour while hauled out
    energy_min_hault: float = 0.25  # energy threshold to trigger haulout decision
    energy_max: float = 1.0  # max energy (normalized)
    min_haulout_hours: int = 4  # minimum continuous haulout duration
    max_at_sea_hours: int = 72  # force haulout if exceeded (dehydration/physiology proxy)
    site_choice_tau: float = 0.5  # softmax temperature for haulout site selection
    site_distance_penalty: float = 0.03  # utility penalty per unit distance
    departure_energy: float = 0.9  # depart haulout when energy >= this

@dataclass
class SealState:
    xy: np.ndarray                # position (x, y)
    energy: float = 0.9
    at_sea: bool = True
    hours_since_haulout: int = 0
    hours_on_haulout: int = 0
    current_site: int | None = None

class SealIBM:
    def __init__(self, env: Environment, params: IBMParams, n_agents: int, rng: np.random.Generator | None = None):
        self.env = env
        self.prm = params
        self.n = n_agents
        self.rng = rng or np.random.default_rng(42)
        self.states: list[SealState] = []
        self._init_agents()

    def _init_agents(self):
        xmin, xmax, ymin, ymax = self.env.bounds
        for _ in range(self.n):
            xy = np.array([self.rng.uniform(xmin, xmax), self.rng.uniform(ymin, ymax)], dtype=float)
            self.states.append(SealState(xy=xy))

    def _choose_haulout_site(self, xy: np.ndarray) -> int:
        if len(self.env.haulout_sites) == 0:
            return -1
        # utility = site_quality - distance_penalty * distance
        dists = np.linalg.norm(self.env.haulout_sites - xy[None, :], axis=1)
        base = np.zeros(len(dists)) if self.env.site_quality is None else np.array(self.env.site_quality, dtype=float)
        util = base - self.prm.site_distance_penalty * dists
        probs = softmax(util, tau=self.prm.site_choice_tau)
        return int(self.rng.choice(len(dists), p=probs))

    def _step_at_sea(self, s: SealState):
        # energy dynamics
        s.energy = max(0.0, s.energy - self.prm.metabolic_cost * self.prm.dt_h)

        # foraging gain ~ habitat value
        hval = self.env.habitat_value(s.xy)
        s.energy = min(self.prm.energy_max, s.energy + self.prm.foraging_gain_scale * hval * self.prm.dt_h)

        s.hours_since_haulout += 1

        # movement: diffusive + biased by habitat gradient
        grad = self.env.gradient(s.xy)
        if np.linalg.norm(grad) > 0:
            grad = grad / np.linalg.norm(grad)
        step = self.rng.normal(0, self.prm.diffusive_sigma, size=2) + self.prm.bias_strength * grad
        # limit to speed_max
        L = np.linalg.norm(step)
        if L > self.prm.speed_max:
            step = step / L * self.prm.speed_max
        s.xy = reflect_into_bounds(s.xy + step, self.env.bounds)

        # haulout decision
        need_haulout = (s.energy <= self.prm.energy_min_hault) or (s.hours_since_haulout >= self.prm.max_at_sea_hours)
        if need_haulout and len(self.env.haulout_sites) > 0:
            idx = self._choose_haulout_site(s.xy)
            if idx >= 0:
                s.current_site = idx
                s.xy = self.env.haulout_sites[idx].copy()
                s.at_sea = False
                s.hours_on_haulout = 0

    def _step_haulout(self, s: SealState):
        s.hours_on_haulout += 1
        s.energy = min(self.prm.energy_max, s.energy + self.prm.haulout_recovery * self.prm.dt_h)

        # minimum rest + depart when recovered
        if s.hours_on_haulout >= self.prm.min_haulout_hours and s.energy >= self.prm.departure_energy:
            s.at_sea = True
            s.hours_since_haulout = 0
            s.current_site = None
            # small push off the site to start at-sea movement
            s.xy = reflect_into_bounds(s.xy + self.rng.normal(0, 0.5, size=2), self.env.bounds)

    def step(self):
        for s in self.states:
            if s.at_sea:
                self._step_at_sea(s)
            else:
                self._step_haulout(s)

    def run(self, T: int) -> pd.DataFrame:
        """Run simulation for T time steps.

        Optimized: pre-allocates arrays instead of appending dicts in a loop.
        """
        n_records = T * self.n

        # Pre-allocate output arrays
        t_col: np.ndarray = np.repeat(np.arange(T), self.n)
        agent_col: np.ndarray = np.tile(np.arange(self.n), T)
        x_col: np.ndarray = np.empty(n_records, dtype=np.float64)
        y_col: np.ndarray = np.empty(n_records, dtype=np.float64)
        energy_col: np.ndarray = np.empty(n_records, dtype=np.float64)
        at_sea_col: np.ndarray = np.empty(n_records, dtype=np.int8)
        haulout_col: np.ndarray = np.empty(n_records, dtype=np.int32)

        for t in range(T):
            start_idx = t * self.n
            for i, s in enumerate(self.states):
                idx = start_idx + i
                x_col[idx] = s.xy[0]
                y_col[idx] = s.xy[1]
                energy_col[idx] = s.energy
                at_sea_col[idx] = int(s.at_sea)
                haulout_col[idx] = -1 if s.current_site is None else s.current_site
            self.step()

        return pd.DataFrame({
            "t": t_col,
            "agent": agent_col,
            "x": x_col,
            "y": y_col,
            "energy": energy_col,
            "at_sea": at_sea_col,
            "haulout_site": haulout_col,
        })

# -----------------------------
# Example: quick demonstration (synthetic)
# -----------------------------

def demo_synthetic():
    rng = np.random.default_rng(123)

    # ---- I‑HTR example (3 haulout clusters, synthetic P) ----
    P = np.array([
        [0.85, 0.10, 0.05],
        [0.10, 0.80, 0.10],
        [0.05, 0.15, 0.80],
    ])
    ihtr_cfg = IHTRConfig(P=P, n_agents=50, T=24*7)  # one week
    ihtr_df = simulate_IHTR(ihtr_cfg, random_state=123)

    # ---- Environment for IBM (synthetic 50x50 habitat) ----
    Nx = Ny = 50
    # create a couple of "good habitat" lobes
    X, Y = np.meshgrid(np.linspace(-2, 2, Nx), np.linspace(-2, 2, Ny))
    habitat = (
        np.exp(-((X - 0.8)**2 + (Y - 0.5)**2) / 0.6) +
        0.6 * np.exp(-((X + 0.9)**2 + (Y + 0.7)**2) / 0.5)
    )
    habitat = (habitat - habitat.min()) / (habitat.max() - habitat.min())  # [0,1]

    bounds = (0.0, 100.0, 0.0, 100.0)
    # map raster to bounds linearly; cellsize chosen so raster covers bounds
    env = Environment(
        bounds=bounds,
        habitat=habitat,
        cellsize=(bounds[1] - bounds[0]) / Nx,
        haulout_sites=np.array([[20, 80], [75, 70], [25, 25], [80, 20]], dtype=float),
        site_quality=np.array([0.3, 0.5, 0.2, 0.4])
    )

    prm = IBMParams()
    ibm = SealIBM(env=env, params=prm, n_agents=60, rng=rng)
    ibm_df = ibm.run(T=24*10)  # 10 days

    # Summaries (minimal)
    ihtr_summary = ihtr_df.groupby(["t", "cluster"]).size().unstack(fill_value=0)
    ibm_usage = ibm_df.groupby("at_sea").size().rename(index={0: "hauled_out", 1: "at_sea"})
    (
        ibm_df.sort_values(["agent", "t"])
              .assign(change=lambda d: (d["at_sea"].diff().fillna(0) != 0).astype(int))
    )

    return {
        "ihtr": ihtr_df,
        "ihtr_summary": ihtr_summary,
        "ibm": ibm_df,
        "ibm_usage_counts": ibm_usage
    }

if __name__ == "__main__":
    res = demo_synthetic()
    # Example: print quick summaries
    print("I-HTR weekly counts by cluster (head):")
    print(res["ihtr_summary"].head())
    print("\nIBM usage counts (at-sea vs hauled-out):")
    print(res["ibm_usage_counts"])