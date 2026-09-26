"""JSON safety of real-world data and GeoDataFrame reprojection.

P1 and P2 of docs/2026-09-26-codebase-review.md. Shiny serialises custom
messages with the standard json module, so any pandas or numpy scalar left in a
payload raised TypeError inside an Effect and closed the session. And a
GeoDataFrame in a projected CRS (UTM, LKS94) was sent in metres, so it drew
nowhere, without a warning.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import warnings
from decimal import Decimal

import pytest

from conftest import _FakeSession
from shiny_deckgl import MapWidget, scatterplot_layer
from shiny_deckgl._data_utils import _serialise_data, json_safe

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")


def _strict(obj) -> str:
    return json.dumps(obj, allow_nan=False)


# ---------------------------------------------------------------------------
# P1 -- json_safe
# ---------------------------------------------------------------------------

class TestJsonSafeTypes:
    @pytest.mark.parametrize("value,expected", [
        (np.int64(3), 3),
        (np.int32(-2), -2),
        (np.uint8(255), 255),
        (np.float32(1.5), 1.5),
        (np.float64("nan"), None),
        (np.float64("inf"), None),
        (np.bool_(True), True),
        (np.array([[1, 2], [3, 4]]), [[1, 2], [3, 4]]),
        (np.array([1.0, np.nan]), [1.0, None]),
        (pd.Timestamp("2024-05-01 12:30"), "2024-05-01T12:30:00"),
        (pd.NaT, None),
        (pd.NA, None),
        (np.datetime64("2024-05-01"), "2024-05-01"),
        (np.datetime64("NaT"), None),
        (dt.datetime(2024, 5, 1, 8), "2024-05-01T08:00:00"),
        (dt.date(2024, 5, 1), "2024-05-01"),
        (dt.timedelta(minutes=2), 120.0),
        (pd.Timedelta(seconds=90), 90.0),
        (Decimal("2.5"), 2.5),
        (pd.Series([1, 2]), [1, 2]),
    ])
    def test_value_becomes_plain_json(self, value, expected):
        got = json_safe(value)
        assert got == expected
        _strict(got)

    def test_plain_values_are_untouched(self):
        payload = {"a": [1, 2.5, "x", None, True], "b": {"c": (1, 2)}}
        assert json_safe(payload) == {"a": [1, 2.5, "x", None, True], "b": {"c": [1, 2]}}

    def test_dataframe_with_dates_and_gaps_serialises(self):
        df = pd.DataFrame({
            "t": pd.to_datetime(["2024-01-01", None]),
            "v": [np.int64(1), np.int64(2)],
            "w": [0.5, np.nan],
        })
        _strict(json_safe(_serialise_data(df)))


class TestPayloadsAreStrictJson:
    df = pd.DataFrame({
        "lon": [21.1, 21.2], "lat": [55.7, 55.8],
        "t": pd.to_datetime(["2024-01-01", None]),
    })

    def _sent(self, coro_fn):
        s = _FakeSession()
        asyncio.run(coro_fn(s))
        for _name, payload in s.messages:
            _strict(payload)
        return s.messages

    def test_update_with_numpy_props_and_dates(self):
        w = MapWidget("m")
        lyr = scatterplot_layer("pts", self.df, getPosition="@@=[d.lon, d.lat]",
                                getRadius=np.int64(100))
        self._sent(lambda s: w.update(s, [lyr]))

    def test_set_source_data(self):
        w = MapWidget("m")
        self._sent(lambda s: w.set_source_data(s, "src", self.df))

    def test_add_source(self):
        w = MapWidget("m")
        spec = {"type": "geojson", "data": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"v": np.float64("nan"), "n": np.int64(1)},
             "geometry": {"type": "Point", "coordinates": [21.1, 55.7]}}]}}
        self._sent(lambda s: w.add_source(s, "src", spec))

    def test_add_cluster_layer(self):
        w = MapWidget("m")
        self._sent(lambda s: w.add_cluster_layer(s, "src", self.df))


# ---------------------------------------------------------------------------
# P2 -- GeoDataFrame CRS
# ---------------------------------------------------------------------------

gpd = pytest.importorskip("geopandas")
shapely_geometry = pytest.importorskip("shapely.geometry")
Point = shapely_geometry.Point


def _coords(fc):
    return fc["features"][0]["geometry"]["coordinates"]


class TestGeoDataFrameCrs:
    klaipeda = (21.13, 55.71)

    def test_projected_frame_is_reprojected_to_lon_lat(self):
        gdf = gpd.GeoDataFrame({"n": [1]}, geometry=[Point(*self.klaipeda)], crs=4326)
        lks = gdf.to_crs(3346)  # LKS94, metres
        lon, lat = _coords(_serialise_data(lks))
        assert lon == pytest.approx(self.klaipeda[0], abs=1e-6)
        assert lat == pytest.approx(self.klaipeda[1], abs=1e-6)

    def test_utm_frame_is_reprojected(self):
        gdf = gpd.GeoDataFrame(geometry=[Point(*self.klaipeda)], crs=4326).to_crs(32634)
        lon, lat = _coords(_serialise_data(gdf))
        assert (lon, lat) == pytest.approx(self.klaipeda, abs=1e-6)

    def test_caller_frame_is_not_modified(self):
        gdf = gpd.GeoDataFrame(geometry=[Point(*self.klaipeda)], crs=4326).to_crs(3346)
        before = gdf.geometry.iloc[0].x
        _serialise_data(gdf)
        assert gdf.crs.to_epsg() == 3346
        assert gdf.geometry.iloc[0].x == before

    def test_lon_lat_frame_passes_through(self):
        gdf = gpd.GeoDataFrame(geometry=[Point(*self.klaipeda)], crs=4326)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert tuple(_coords(_serialise_data(gdf))) == pytest.approx(self.klaipeda)

    def test_missing_crs_with_metre_coordinates_warns(self):
        gdf = gpd.GeoDataFrame(geometry=[Point(500000.0, 6170000.0)])
        with pytest.warns(UserWarning, match="no CRS"):
            _serialise_data(gdf)

    def test_missing_crs_with_lon_lat_coordinates_is_quiet(self):
        gdf = gpd.GeoDataFrame(geometry=[Point(*self.klaipeda)])
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _serialise_data(gdf)


# ---------------------------------------------------------------------------
# P9 -- colour helpers on real data
# ---------------------------------------------------------------------------

from shiny_deckgl import color_bins, color_quantiles, color_range  # noqa: E402

MISSING = [0, 0, 0, 0]


class TestColourHelpersOnRealData:
    @pytest.mark.parametrize("fn", [color_bins, color_quantiles])
    def test_nan_gets_the_missing_colour_and_others_are_unaffected(self, fn):
        clean = fn([1.0, 2.0, 3.0, 4.0], n_bins=4)
        got = fn([1.0, float("nan"), 2.0, 3.0, None, 4.0, float("inf")], n_bins=4)
        assert got[1] == MISSING and got[4] == MISSING and got[6] == MISSING
        assert [got[0], got[2], got[3], got[5]] == clean

    @pytest.mark.parametrize("fn", [color_bins, color_quantiles])
    def test_series_and_arrays_are_accepted(self, fn):
        expected = fn([5.0, 1.0, 3.0], n_bins=3)
        assert fn(pd.Series([5.0, 1.0, 3.0]), n_bins=3) == expected
        assert fn(np.array([5.0, 1.0, 3.0]), n_bins=3) == expected
        assert fn(pd.Series([5, 1, 3], dtype="Int64"), n_bins=3) == expected

    @pytest.mark.parametrize("fn", [color_bins, color_quantiles])
    def test_all_missing(self, fn):
        assert fn([float("nan"), None], n_bins=3) == [MISSING, MISSING]

    def test_custom_missing_colour(self):
        got = color_bins([1.0, float("nan")], n_bins=2, missing_color=[9, 9, 9, 255])
        assert got[1] == [9, 9, 9, 255]

    def test_quantile_breaks_ignore_nan(self):
        # NaN used to sort to an arbitrary place and corrupt the breaks.
        vals = [1.0, 2.0, 3.0, 4.0]
        top = color_range(4)[-1]
        assert color_quantiles(vals + [float("nan")] * 4, n_bins=4)[3] == top


class TestColourHelperOverflow:
    """1.11.1: float(10**400) raised an uncaught OverflowError."""

    @pytest.mark.parametrize("fn", [color_bins, color_quantiles])
    def test_too_large_integer_is_treated_as_missing(self, fn):
        clean = fn([1, 2, 3], n_bins=3)
        got = fn([1, 10**400, 2, 3], n_bins=3)
        assert got[1] == MISSING
        assert [got[0], got[2], got[3]] == clean
