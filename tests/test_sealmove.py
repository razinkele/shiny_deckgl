"""Tests for the _sealmove module (seal movement simulation).

Tests cover:
- Utility functions (normalize_rows, softmax, reflect_into_bounds, gradient_field)
- IHTRConfig and simulate_IHTR
- Environment class
- IBMParams dataclass
- SealState dataclass
- SealIBM simulation class
"""
from __future__ import annotations

import pytest

# Skip all tests if numpy/pandas not installed
np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

from shiny_deckgl._sealmove import (
    Environment,
    IBMParams,
    IHTRConfig,
    SealIBM,
    SealState,
    gradient_field,
    normalize_rows,
    reflect_into_bounds,
    simulate_IHTR,
    softmax,
)


# ---------------------------------------------------------------------------
# Test normalize_rows utility
# ---------------------------------------------------------------------------

class TestNormalizeRows:
    """Tests for the normalize_rows matrix normalization function."""

    def test_rows_sum_to_one(self):
        """Normalized rows should sum to 1."""
        M = np.array([[1, 2, 3], [4, 5, 6]])
        result = normalize_rows(M)
        row_sums = result.sum(axis=1)
        np.testing.assert_allclose(row_sums, [1.0, 1.0])

    def test_single_row(self):
        """Single row matrix should work."""
        M = np.array([[2, 4, 4]])
        result = normalize_rows(M)
        expected = np.array([[0.2, 0.4, 0.4]])
        np.testing.assert_allclose(result, expected)

    def test_zero_row_handled(self):
        """Zero row should not cause division by zero."""
        M = np.array([[0, 0, 0], [1, 1, 1]])
        result = normalize_rows(M)
        # Zero row stays zero (divided by 1.0)
        np.testing.assert_allclose(result[0], [0, 0, 0])
        np.testing.assert_allclose(result[1], [1/3, 1/3, 1/3])

    def test_preserves_shape(self):
        """Output should have same shape as input."""
        M = np.array([[1, 2], [3, 4], [5, 6]])
        result = normalize_rows(M)
        assert result.shape == M.shape

    def test_returns_float_array(self):
        """Result should be float dtype."""
        M = np.array([[1, 2, 3]], dtype=int)
        result = normalize_rows(M)
        assert result.dtype == float


# ---------------------------------------------------------------------------
# Test softmax utility
# ---------------------------------------------------------------------------

class TestSoftmax:
    """Tests for the temperature-scaled softmax function."""

    def test_sums_to_one(self):
        """Softmax output should sum to 1."""
        x = np.array([1.0, 2.0, 3.0])
        result = softmax(x)
        np.testing.assert_allclose(result.sum(), 1.0)

    def test_preserves_order(self):
        """Higher input values should have higher probabilities."""
        x = np.array([1.0, 2.0, 3.0])
        result = softmax(x)
        assert result[2] > result[1] > result[0]

    def test_equal_inputs(self):
        """Equal inputs should give equal probabilities."""
        x = np.array([5.0, 5.0, 5.0])
        result = softmax(x)
        np.testing.assert_allclose(result, [1/3, 1/3, 1/3])

    def test_temperature_effect_high(self):
        """High temperature should flatten the distribution."""
        x = np.array([0.0, 10.0])
        result_low_temp = softmax(x, tau=0.1)
        result_high_temp = softmax(x, tau=10.0)
        # High temp should be more uniform
        assert abs(result_high_temp[0] - result_high_temp[1]) < \
               abs(result_low_temp[0] - result_low_temp[1])

    def test_temperature_effect_low(self):
        """Low temperature should sharpen the distribution."""
        x = np.array([0.0, 1.0])
        result = softmax(x, tau=0.01)
        # Very low temp: winner takes almost all
        assert result[1] > 0.99

    def test_numerical_stability(self):
        """Should handle large values without overflow."""
        x = np.array([1000.0, 1001.0, 1002.0])
        result = softmax(x)
        assert not np.isnan(result).any()
        assert not np.isinf(result).any()
        np.testing.assert_allclose(result.sum(), 1.0)

    def test_negative_values(self):
        """Should handle negative values."""
        x = np.array([-5.0, -3.0, -1.0])
        result = softmax(x)
        np.testing.assert_allclose(result.sum(), 1.0)
        assert result[2] > result[1] > result[0]

    def test_single_element(self):
        """Single element should return 1.0."""
        x = np.array([5.0])
        result = softmax(x)
        np.testing.assert_allclose(result, [1.0])


# ---------------------------------------------------------------------------
# Test reflect_into_bounds utility
# ---------------------------------------------------------------------------

class TestReflectIntoBounds:
    """Tests for boundary reflection function."""

    def test_inside_bounds_unchanged(self):
        """Point inside bounds should be unchanged."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([5.0, 5.0])
        result = reflect_into_bounds(xy, bounds)
        np.testing.assert_allclose(result, [5.0, 5.0])

    def test_reflect_left(self):
        """Point past left boundary should reflect."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([-2.0, 5.0])
        result = reflect_into_bounds(xy, bounds)
        assert result[0] == 2.0  # Reflected
        assert result[1] == 5.0  # Unchanged

    def test_reflect_right(self):
        """Point past right boundary should reflect."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([12.0, 5.0])
        result = reflect_into_bounds(xy, bounds)
        assert result[0] == 8.0  # Reflected: 10 - (12 - 10) = 8
        assert result[1] == 5.0

    def test_reflect_bottom(self):
        """Point past bottom boundary should reflect."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([5.0, -3.0])
        result = reflect_into_bounds(xy, bounds)
        assert result[0] == 5.0
        assert result[1] == 3.0  # Reflected

    def test_reflect_top(self):
        """Point past top boundary should reflect."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([5.0, 15.0])
        result = reflect_into_bounds(xy, bounds)
        assert result[0] == 5.0
        assert result[1] == 5.0  # Reflected: 10 - (15 - 10) = 5

    def test_corner_reflection(self):
        """Point past corner should reflect both axes."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([-1.0, 11.0])
        result = reflect_into_bounds(xy, bounds)
        assert result[0] == 1.0  # Reflected from left
        assert result[1] == 9.0  # Reflected from top

    def test_on_boundary(self):
        """Point exactly on boundary should be unchanged."""
        bounds = (0.0, 10.0, 0.0, 10.0)
        xy = np.array([0.0, 10.0])
        result = reflect_into_bounds(xy, bounds)
        np.testing.assert_allclose(result, [0.0, 10.0])


# ---------------------------------------------------------------------------
# Test gradient_field utility
# ---------------------------------------------------------------------------

class TestGradientField:
    """Tests for gradient field computation."""

    def test_flat_surface_zero_gradient(self):
        """Flat surface should have zero gradient."""
        raster = np.ones((10, 10)) * 5.0
        gx, gy = gradient_field(raster)
        np.testing.assert_allclose(gx, 0.0, atol=1e-10)
        np.testing.assert_allclose(gy, 0.0, atol=1e-10)

    def test_slope_x_direction(self):
        """Gradient should detect X-direction slope."""
        raster = np.array([[1, 2, 3], [1, 2, 3], [1, 2, 3]], dtype=float)
        gx, gy = gradient_field(raster)
        # Should have positive X gradient
        assert np.all(gx[:, 1] > 0)  # Middle column has positive gradient

    def test_slope_y_direction(self):
        """Gradient should detect Y-direction slope."""
        raster = np.array([[1, 1, 1], [2, 2, 2], [3, 3, 3]], dtype=float)
        gx, gy = gradient_field(raster)
        # Should have positive Y gradient
        assert np.all(gy[1, :] > 0)  # Middle row has positive gradient

    def test_output_shape(self):
        """Output should match input shape."""
        raster = np.random.rand(15, 20)
        gx, gy = gradient_field(raster)
        assert gx.shape == raster.shape
        assert gy.shape == raster.shape


# ---------------------------------------------------------------------------
# Test IHTRConfig dataclass
# ---------------------------------------------------------------------------

class TestIHTRConfig:
    """Tests for IHTRConfig configuration class."""

    def test_default_values(self):
        """Should have sensible defaults."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P)
        assert cfg.n_agents == 100
        assert cfg.T == 24 * 30
        assert cfg.initial_dist is None

    def test_custom_values(self):
        """Should accept custom values."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=50, T=100)
        assert cfg.n_agents == 50
        assert cfg.T == 100


# ---------------------------------------------------------------------------
# Test simulate_IHTR function
# ---------------------------------------------------------------------------

class TestSimulateIHTR:
    """Tests for the IHTR simulation function."""

    def test_returns_dataframe(self):
        """Should return a pandas DataFrame."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=10, T=5)
        result = simulate_IHTR(cfg)
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_columns(self):
        """DataFrame should have expected columns."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=10, T=5)
        result = simulate_IHTR(cfg)
        assert list(result.columns) == ["t", "agent", "cluster"]

    def test_dataframe_length(self):
        """DataFrame should have T * n_agents rows."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=10, T=5)
        result = simulate_IHTR(cfg)
        assert len(result) == 10 * 5

    def test_cluster_values_valid(self):
        """All cluster values should be valid state indices."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=10, T=5)
        result = simulate_IHTR(cfg)
        assert result["cluster"].min() >= 0
        assert result["cluster"].max() < 2  # K=2 states

    def test_deterministic_with_seed(self):
        """Same seed should produce same results."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        cfg = IHTRConfig(P=P, n_agents=10, T=5)
        result1 = simulate_IHTR(cfg, random_state=42)
        result2 = simulate_IHTR(cfg, random_state=42)
        pd.testing.assert_frame_equal(result1, result2)

    def test_initial_distribution(self):
        """Custom initial distribution should be used."""
        P = np.array([[0.9, 0.1], [0.2, 0.8]])
        # All agents start in cluster 1
        init_dist = np.array([0.0, 1.0])
        cfg = IHTRConfig(P=P, n_agents=10, T=1, initial_dist=init_dist)
        result = simulate_IHTR(cfg, random_state=42)
        # At t=0, all should be in cluster 1
        t0 = result[result["t"] == 0]
        assert (t0["cluster"] == 1).all()


# ---------------------------------------------------------------------------
# Test Environment class
# ---------------------------------------------------------------------------

class TestEnvironment:
    """Tests for the Environment class."""

    @pytest.fixture
    def simple_env(self):
        """Create a simple test environment."""
        habitat = np.array([
            [0.2, 0.4, 0.6],
            [0.3, 0.5, 0.7],
            [0.4, 0.6, 0.8],
        ], dtype=float)
        return Environment(
            bounds=(0.0, 10.0, 0.0, 10.0),
            habitat=habitat,
            cellsize=10.0/3,
            haulout_sites=np.array([[2.0, 8.0], [8.0, 2.0]]),
            site_quality=np.array([0.5, 0.3]),
        )

    def test_habitat_value_center(self, simple_env):
        """Should sample habitat value at center."""
        # Center of bounds
        value = simple_env.habitat_value(np.array([5.0, 5.0]))
        assert 0.0 <= value <= 1.0

    def test_habitat_value_corner(self, simple_env):
        """Should sample habitat value at corner."""
        value = simple_env.habitat_value(np.array([0.0, 0.0]))
        assert value == pytest.approx(0.2, abs=0.1)  # Bottom-left of habitat

    def test_habitat_value_outside_bounds(self, simple_env):
        """Outside bounds should return 0."""
        value = simple_env.habitat_value(np.array([-5.0, -5.0]))
        assert value == 0.0

    def test_gradient_returns_2d(self, simple_env):
        """Gradient should return 2D vector."""
        grad = simple_env.gradient(np.array([5.0, 5.0]))
        assert grad.shape == (2,)

    def test_gradient_cached(self, simple_env):
        """Gradient field should be computed and cached."""
        _ = simple_env.gradient(np.array([5.0, 5.0]))
        assert hasattr(simple_env, "_gx")
        assert hasattr(simple_env, "_gy")


# ---------------------------------------------------------------------------
# Test IBMParams dataclass
# ---------------------------------------------------------------------------

class TestIBMParams:
    """Tests for IBMParams configuration class."""

    def test_default_values(self):
        """Should have sensible defaults."""
        params = IBMParams()
        assert params.dt_h == 1.0
        assert params.speed_max == 2.0
        assert params.energy_max == 1.0
        assert params.min_haulout_hours == 4

    def test_custom_values(self):
        """Should accept custom values."""
        params = IBMParams(speed_max=5.0, energy_max=2.0)
        assert params.speed_max == 5.0
        assert params.energy_max == 2.0


# ---------------------------------------------------------------------------
# Test SealState dataclass
# ---------------------------------------------------------------------------

class TestSealState:
    """Tests for SealState dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        state = SealState(xy=np.array([5.0, 5.0]))
        assert state.energy == 0.9
        assert state.at_sea is True
        assert state.hours_since_haulout == 0
        assert state.hours_on_haulout == 0
        assert state.current_site is None

    def test_custom_values(self):
        """Should accept custom values."""
        state = SealState(
            xy=np.array([5.0, 5.0]),
            energy=0.5,
            at_sea=False,
            current_site=1,
        )
        assert state.energy == 0.5
        assert state.at_sea is False
        assert state.current_site == 1


# ---------------------------------------------------------------------------
# Test SealIBM simulation class
# ---------------------------------------------------------------------------

class TestSealIBM:
    """Tests for the SealIBM simulation class."""

    @pytest.fixture
    def simple_ibm(self):
        """Create a simple test IBM."""
        habitat = np.random.rand(20, 20)
        env = Environment(
            bounds=(0.0, 100.0, 0.0, 100.0),
            habitat=habitat,
            haulout_sites=np.array([[20.0, 80.0], [80.0, 20.0]]),
        )
        params = IBMParams()
        return SealIBM(env=env, params=params, n_agents=5, rng=np.random.default_rng(42))

    def test_init_creates_agents(self, simple_ibm):
        """Should create n_agents seal states."""
        assert len(simple_ibm.states) == 5

    def test_agents_start_in_bounds(self, simple_ibm):
        """All agents should start within bounds."""
        for state in simple_ibm.states:
            assert 0.0 <= state.xy[0] <= 100.0
            assert 0.0 <= state.xy[1] <= 100.0

    def test_step_changes_state(self, simple_ibm):
        """A step should change agent positions."""
        initial_positions = [s.xy.copy() for s in simple_ibm.states]
        simple_ibm.step()
        # At least some positions should change
        changed = False
        for i, state in enumerate(simple_ibm.states):
            if not np.allclose(state.xy, initial_positions[i]):
                changed = True
                break
        assert changed

    def test_run_returns_dataframe(self, simple_ibm):
        """run() should return a DataFrame."""
        result = simple_ibm.run(T=10)
        assert isinstance(result, pd.DataFrame)

    def test_run_dataframe_columns(self, simple_ibm):
        """DataFrame should have expected columns."""
        result = simple_ibm.run(T=10)
        expected_cols = {"t", "agent", "x", "y", "energy", "at_sea", "haulout_site"}
        assert set(result.columns) == expected_cols

    def test_run_dataframe_length(self, simple_ibm):
        """DataFrame should have T * n_agents rows."""
        result = simple_ibm.run(T=10)
        assert len(result) == 10 * 5

    def test_energy_bounded(self, simple_ibm):
        """Energy should stay in valid range."""
        result = simple_ibm.run(T=100)
        assert result["energy"].min() >= 0.0
        assert result["energy"].max() <= simple_ibm.prm.energy_max

    def test_positions_in_bounds(self, simple_ibm):
        """Positions should stay within bounds."""
        result = simple_ibm.run(T=100)
        assert result["x"].min() >= 0.0
        assert result["x"].max() <= 100.0
        assert result["y"].min() >= 0.0
        assert result["y"].max() <= 100.0

    def test_deterministic_with_seed(self):
        """Same seed should produce same results."""
        habitat = np.random.rand(20, 20)
        env = Environment(
            bounds=(0.0, 100.0, 0.0, 100.0),
            habitat=habitat,
            haulout_sites=np.array([[20.0, 80.0]]),
        )
        params = IBMParams()

        ibm1 = SealIBM(env=env, params=params, n_agents=3, rng=np.random.default_rng(123))
        ibm2 = SealIBM(env=env, params=params, n_agents=3, rng=np.random.default_rng(123))

        result1 = ibm1.run(T=10)
        result2 = ibm2.run(T=10)

        pd.testing.assert_frame_equal(result1, result2)


# ---------------------------------------------------------------------------
# Test demo_synthetic function
# ---------------------------------------------------------------------------

class TestDemoSynthetic:
    """Tests for the demo_synthetic function."""

    def test_returns_dict(self):
        """Should return a dictionary with expected keys."""
        from shiny_deckgl._sealmove import demo_synthetic
        result = demo_synthetic()
        assert isinstance(result, dict)
        assert "ihtr" in result
        assert "ihtr_summary" in result
        assert "ibm" in result
        assert "ibm_usage_counts" in result

    def test_ihtr_is_dataframe(self):
        """ihtr result should be a DataFrame."""
        from shiny_deckgl._sealmove import demo_synthetic
        result = demo_synthetic()
        assert isinstance(result["ihtr"], pd.DataFrame)

    def test_ibm_is_dataframe(self):
        """ibm result should be a DataFrame."""
        from shiny_deckgl._sealmove import demo_synthetic
        result = demo_synthetic()
        assert isinstance(result["ibm"], pd.DataFrame)
