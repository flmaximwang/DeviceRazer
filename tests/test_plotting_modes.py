"""
Regression tests for the plotting modes of ``Signal1DCollection``.

Covers two bugs:

- **Bug 9** — ``Signal1DCollection.plot(mode=N)`` ignored its ``mode``
  argument: the method only ever read ``plot_args.mode``, so every call
  silently drew the configured mode (``examples/*`` call ``plot(mode=1)``).
- **Bug 10** — after ``set_default_annotations()``, modes 1 and 2 raised
  ``AssertionError: ticklabel_space_major is not set``: the tick spacing was
  only inferred for the collection annotation, never copied down to the
  per-signal annotations that modes 1 and 2 actually draw.  The continuous
  override additionally set neither the per-signal axis spacing nor the
  per-signal value spacing.

Honouring ``mode`` also exposes mode 1 to collections whose visible signals
are not all continuous (Chrom/ChemsStation include a discrete fraction log);
mode 1 must draw those on the primary Axes instead of raising, otherwise the
``plot(mode=1)`` calls in ``examples/`` still fail.  Likewise mode 2
(``plot_separately``) must not assume every signal has continuous value
annotations: discrete signals have no ``value_annotation.ticks``, so their
subplot gets ``ylim (0, 1)`` and no y ticks.

The tests use the ``Agg`` backend (no display needed) and close every figure.
"""

import sys

sys.path.append("..")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from dvrazer.abstract.signal_1d import ContinuousSignal1D, DiscreteSignal1D
from dvrazer.abstract.signal_1d_collection import (
    Signal1DCollection,
    ContinuousSignal1DCollection,
)

#: (name, axis, values) triples with deliberately different axis/value ranges,
#: so that the aligned collection range differs from every individual range.
SIGNAL_SPECS = [
    ("sample a", [0.0, 1.0, 2.0], [1.0, 2.0, 3.0]),
    ("sample b", [0.0, 2.0, 4.0], [3.0, 2.0, 1.5]),
    ("sample c", [10.0, 20.0, 30.0], [0.5, 1.5, 2.5]),
]

COLLECTION_CLASSES = [Signal1DCollection, ContinuousSignal1DCollection]


def make_continuous_signal(
    name: str, axis: list[float], values: list[float]
) -> ContinuousSignal1D:
    """Build a small ``ContinuousSignal1D`` with the given data."""
    data = pd.DataFrame({"axis": axis, "value": values})
    return ContinuousSignal1D.from_data(
        data=data,
        name=name,
        axis_name="Time",
        axis_unit="s",
        value_name="Absorbance",
        value_unit="AU",
    )


def make_discrete_signal(
    name: str, axis: list[float], values: list[float]
) -> DiscreteSignal1D:
    """Build a small ``DiscreteSignal1D`` (e.g. a collected-fraction log)."""
    data = pd.DataFrame({"axis": axis, "value": values})
    return DiscreteSignal1D.from_data(
        data=data,
        name=name,
        axis_name="Time",
        axis_unit="min",
        value_name="Fraction",
        value_unit=None,
    )


def make_collection(collection_cls, name: str = "test collection"):
    """Build a collection of three similar continuous signals."""
    signals = [make_continuous_signal(*spec) for spec in SIGNAL_SPECS]
    return collection_cls.from_similar_signals(signals, name=name)


def make_mixed_collection(discrete_first: bool) -> Signal1DCollection:
    """Build a collection with two continuous signals + one discrete log."""
    continuous = [
        make_continuous_signal("uv", [0.0, 1.0, 2.0], [1.0, 2.0, 3.0]),
        make_continuous_signal("cond", [0.0, 2.0, 4.0], [3.0, 2.0, 1.5]),
    ]
    fractions = make_discrete_signal("fractions", [0.0, 1.0, 2.0], [1.0, 0.0, 1.0])
    signals = (
        ([fractions] + continuous) if discrete_first else (continuous + [fractions])
    )
    return Signal1DCollection.from_similar_signals(signals, name="mixed")


def flatten(axes_list) -> list:
    """Flatten the 2-D axes grid returned by mode 2."""
    return [ax for row in axes_list for ax in row]


@pytest.fixture(autouse=True)
def close_figures():
    """Make sure no figure leaks between tests."""
    plt.close("all")
    yield
    plt.close("all")


class TestPlotModeKeyword:
    """Bug 9: ``plot(mode=...)`` must select the layout for that call only."""

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_mode_keyword_selects_layout_and_keeps_plot_args_untouched(
        self, collection_cls
    ):
        collection = make_collection(collection_cls)
        collection.set_default_annotations()
        assert collection.plot_args.mode == 0

        # mode 0 → a single Axes
        fig, ax = collection.plot(mode=0)
        assert isinstance(ax, plt.Axes)
        assert len(fig.axes) == 1
        assert collection.plot_args.mode == 0, "plot(mode=0) mutated plot_args.mode"
        plt.close(fig)

        # mode 1 → one Axes per continuous signal (primary + twin y-axes)
        fig, axes = collection.plot(mode=1)
        assert isinstance(axes, list)
        assert len(axes) == len(SIGNAL_SPECS)
        assert all(isinstance(current_ax, plt.Axes) for current_ax in axes)
        assert len(fig.axes) == len(axes)
        assert collection.plot_args.mode == 0, "plot(mode=1) mutated plot_args.mode"
        plt.close(fig)

        # mode 2 → a 2-D grid with at least one subplot per visible signal
        fig, axes = collection.plot(mode=2)
        assert isinstance(axes, list)
        assert all(isinstance(row, list) for row in axes)
        flat_axes = flatten(axes)
        assert len(flat_axes) >= len(SIGNAL_SPECS)
        assert all(isinstance(current_ax, plt.Axes) for current_ax in flat_axes)
        assert len(fig.axes) == len(flat_axes)
        assert collection.plot_args.mode == 0, "plot(mode=2) mutated plot_args.mode"
        plt.close(fig)

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_mode_keyword_overrides_nonzero_plot_args_mode(self, collection_cls):
        """The kwarg must win even when plot_args.mode is already set."""
        collection = make_collection(collection_cls)
        collection.set_default_annotations()
        collection.plot_args.mode = 2

        fig, ax = collection.plot(mode=0)
        assert isinstance(ax, plt.Axes)
        assert collection.plot_args.mode == 2
        plt.close(fig)

        fig, axes = collection.plot(mode=1)
        assert isinstance(axes, list) and len(axes) == len(SIGNAL_SPECS)
        assert collection.plot_args.mode == 2
        plt.close(fig)

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_plot_without_mode_uses_plot_args_mode(self, collection_cls):
        """Without the kwarg the configured mode is still used."""
        collection = make_collection(collection_cls)
        collection.set_default_annotations()
        collection.plot_args.mode = 1

        fig, axes = collection.plot()
        assert isinstance(axes, list)
        assert len(axes) == len(SIGNAL_SPECS)
        assert len(fig.axes) == len(axes)
        assert collection.plot_args.mode == 1
        plt.close(fig)

    def test_line2d_kwargs_are_forwarded_with_mode_keyword(self):
        """``mode`` must be popped, the remaining kwargs still reach plot_at."""
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()

        fig, ax = collection.plot(mode=0, linewidth=3.0, linestyle="--")
        assert len(ax.get_lines()) == len(SIGNAL_SPECS)
        for line in ax.get_lines():
            assert line.get_linewidth() == 3.0
            assert line.get_linestyle() == "--"
        plt.close(fig)

    def test_row_and_col_kwargs_are_forwarded_in_mode_2(self):
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()

        fig, axes = collection.plot(mode=2, row=len(SIGNAL_SPECS), col=1)
        assert len(axes) == len(SIGNAL_SPECS)
        assert all(len(row) == 1 for row in axes)
        plt.close(fig)

    def test_unknown_mode_raises(self):
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()

        with pytest.raises(ValueError):
            collection.plot(mode=3)
        assert collection.plot_args.mode == 0
        assert plt.get_fignums() == [], "unknown mode must not create a figure"

    def test_unknown_mode_does_not_measure_margins(self):
        """An invalid mode must be rejected before the tentative figure."""
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()
        collection.plot_args.ax_size = (8, 4)
        assert collection.plot_args.margin is None

        with pytest.raises(ValueError):
            collection.plot(mode=7)
        assert collection.plot_args.margin is None
        assert plt.get_fignums() == []

    def test_fixed_ax_size_with_mode_keyword(self):
        """Chrom-like layout: ax_size set, plot(mode=1) must work and measure."""
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()
        collection.plot_args.ax_size = (16, 5)
        assert collection.plot_args.mode == 0
        assert collection.plot_args.margin is None

        fig, axes = collection.plot(mode=1)
        assert isinstance(axes, list) and len(axes) == len(SIGNAL_SPECS)
        assert collection.plot_args.margin is not None
        assert collection.plot_args.mode == 0
        plt.close(fig)

        # The measured margins are cached; a second plot in another mode works.
        fig, ax = collection.plot(mode=0)
        assert isinstance(ax, plt.Axes)
        plt.close(fig)


class TestDefaultAnnotationsTickSpacing:
    """Bug 10: tick spacing must be copied down to every signal."""

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_per_signal_axis_tick_spacing_is_set(self, collection_cls):
        collection = make_collection(collection_cls)
        collection.set_default_annotations()

        assert collection.axis_annotation.ticklabel_space_major is not None
        assert collection.axis_annotation.ticklabel_space_minor is not None
        for signal in collection.signals:
            axis_annotation = signal.axis_annotation
            assert axis_annotation.ticklabel_space_major is not None
            assert axis_annotation.ticklabel_space_minor is not None
            assert axis_annotation.ticklabel_space_major > 0
            assert axis_annotation.ticklabel_space_minor > 0
            # ticklabels/ticks must be generatable for the aligned axis
            assert len(axis_annotation.ticklabels) > 1

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_per_signal_value_tick_spacing_is_set(self, collection_cls):
        collection = make_collection(collection_cls)
        collection.set_default_annotations()

        assert collection.value_annotation.ticklabel_space_major is not None
        assert collection.value_annotation.ticklabel_space_minor is not None
        for signal in collection.signals:
            value_annotation = signal.value_annotation
            assert value_annotation.ticklabel_space_major is not None
            assert value_annotation.ticklabel_space_minor is not None
            assert value_annotation.ticklabel_space_major > 0
            assert value_annotation.ticklabel_space_minor > 0
            assert len(value_annotation.ticklabels) > 1

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_plot_all_modes_after_set_default_annotations(self, collection_cls):
        """The original failure: set_default_annotations() then plot 0/1/2."""
        collection = make_collection(collection_cls)
        collection.set_default_annotations()

        fig, ax = collection.plot(mode=0)
        assert isinstance(ax, plt.Axes)
        plt.close(fig)

        fig, axes = collection.plot(mode=1)
        assert isinstance(axes, list) and len(axes) == len(SIGNAL_SPECS)
        plt.close(fig)

        fig, axes = collection.plot(mode=2)
        assert len(flatten(axes)) >= len(SIGNAL_SPECS)
        plt.close(fig)

    def test_continuous_collection_sets_collection_minor_spacing(self):
        """The continuous override used to leave the collection minor spacing None."""
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()

        assert collection.axis_annotation.ticklabel_space_minor is not None
        assert collection.value_annotation.ticklabel_space_minor is not None

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_zero_axis_range_raises(self, collection_cls):
        """A zero axis range cannot produce a tick spacing; raise like the base."""
        signals = [
            make_continuous_signal(name, [5.0, 5.0, 5.0], values)
            for name, _, values in SIGNAL_SPECS
        ]
        collection = collection_cls.from_similar_signals(signals)

        with pytest.raises(ValueError):
            collection.set_default_annotations()

    @pytest.mark.parametrize("collection_cls", COLLECTION_CLASSES)
    def test_zero_value_range_falls_back_to_unit_spacing(self, collection_cls):
        """Constant values must not yield a 0 (infinite-loop) tick spacing."""
        signals = [
            make_continuous_signal(name, axis, [2.0, 2.0, 2.0])
            for name, axis, _ in SIGNAL_SPECS
        ]
        collection = collection_cls.from_similar_signals(signals)
        collection.set_default_annotations()

        assert collection.value_annotation.ticklabel_space_major == pytest.approx(1.0)
        assert collection.value_annotation.ticklabel_space_minor == pytest.approx(0.2)
        for signal in collection.signals:
            assert signal.value_annotation.ticklabel_space_major == pytest.approx(1.0)
            assert signal.value_annotation.ticklabel_space_minor == pytest.approx(0.2)

    def test_chrom_default_mode_1_plots_after_set_default_annotations(self):
        """Real-world reproduction: Chrom defaults to mode 1 + ax_size (16, 5)."""
        from dvrazer.concrete.chromatography import Chrom, ChromSig

        def make_chrom_signal(name, axis, values):
            data = pd.DataFrame({"axis": axis, "value": values})
            return ChromSig.from_data(
                data=data,
                name=name,
                axis_name="Time",
                axis_unit="min",
                value_name="Absorbance",
                value_unit="mAU",
            )

        signals = [
            make_chrom_signal("UV", [0.0, 1.0, 2.0], [1.0, 2.0, 3.0]),
            make_chrom_signal("Cond", [0.0, 2.0, 4.0], [3.0, 2.0, 1.5]),
        ]
        chrom = Chrom.from_similar_signals(signals, name="chrom")
        assert chrom.plot_args.mode == 1
        assert chrom.plot_args.ax_size == (16, 5)

        chrom.set_default_annotations()
        fig, axes = chrom.plot()
        assert isinstance(axes, list)
        assert len(axes) == len(signals)
        plt.close(fig)

        # The pre-fix failure for plots without ax_size too:
        chrom.plot_args.ax_size = None
        chrom.plot_args.margin = None
        fig, axes = chrom.plot()
        assert len(axes) == len(signals)
        plt.close(fig)


class TestMode1WithDiscreteSignals:
    """Mode 1 draws discrete signals on the primary Axes, whatever their order."""

    @pytest.mark.parametrize("discrete_first", [True, False])
    def test_discrete_signal_is_drawn_on_primary_axes(self, discrete_first):
        """A leading discrete signal must not raise or swallow the x axis."""
        collection = make_mixed_collection(discrete_first)
        collection.set_default_annotations()

        fig, axes = collection.plot(mode=1)
        assert isinstance(axes, list)
        # one Axes per continuous signal, discrete ones share the primary Axes
        assert len(axes) == 2
        assert len(fig.axes) == len(axes)
        assert collection.plot_args.mode == 0
        plt.close(fig)

    def test_mode_1_without_any_continuous_signal_raises(self):
        signals = [
            make_discrete_signal(name, axis, values)
            for name, axis, values in SIGNAL_SPECS
        ]
        collection = Signal1DCollection.from_similar_signals(signals)

        with pytest.raises(TypeError):
            collection.plot(mode=1)



class TestMode2WithMixedSignals:
    """Bug 10 acceptance: mode 2 must work for continuous + discrete collections."""

    @staticmethod
    def axes_by_signal_name(collection, axes):
        """Map visible signal name -> its subplot (mode 2 titles carry names)."""
        flat_axes = flatten(axes)
        return {
            signal_name: flat_axes[i]
            for i, signal_name in enumerate(collection.visible_signal_names)
        }

    @pytest.mark.parametrize("discrete_first", [True, False])
    def test_plain_collection_with_discrete_signal(self, discrete_first):
        """``set_default_annotations()`` then mode 2 used to raise AttributeError."""
        collection = make_mixed_collection(discrete_first)
        collection.set_default_annotations()

        fig, axes = collection.plot(mode=2)
        assert isinstance(fig, plt.Figure)
        assert isinstance(axes, list) and all(isinstance(row, list) for row in axes)

        flat_axes = flatten(axes)
        assert len(flat_axes) >= len(collection.visible_signal_names)
        # one title per visible signal, in visible order
        titles = [
            ax.get_title() for ax in flat_axes[: len(collection.visible_signal_names)]
        ]
        assert titles == collection.visible_signal_names

        axes_by_name = self.axes_by_signal_name(collection, axes)
        # discrete (fraction log) subplot: fully drawn in [0, 1], no y ticks
        discrete_ax = axes_by_name["fractions"]
        assert list(discrete_ax.get_yticks()) == []
        assert discrete_ax.get_ylim() == (0.0, 1.0)
        assert discrete_ax.get_ylabel() == "Fraction"
        # continuous subplots keep their value ticks/labels
        for signal_name in ("uv", "cond"):
            signal = collection[signal_name]
            continuous_ax = axes_by_name[signal_name]
            assert len(continuous_ax.get_yticks()) > 0
            assert np.allclose(
                continuous_ax.get_yticks(), signal.value_annotation.ticks
            )
            assert [
                text.get_text() for text in continuous_ax.get_yticklabels()
            ] == list(signal.value_annotation.ticklabels)
        assert collection.plot_args.mode == 0
        plt.close(fig)

    def test_continuous_only_mode_2_is_unchanged(self):
        """Regression guard: continuous mode 2 ticks must stay identical."""
        collection = make_collection(ContinuousSignal1DCollection)
        collection.set_default_annotations()

        fig, axes = collection.plot(mode=2)
        flat_axes = flatten(axes)
        assert [len(row) for row in axes] == [2, 2]  # 3 signals -> 2x2 grid
        for i, signal_name in enumerate(collection.visible_signal_names):
            signal = collection[signal_name]
            current_ax = flat_axes[i]
            assert current_ax.get_title() == signal_name
            assert current_ax.get_ylim() == (0.0, 1.0)
            assert np.allclose(current_ax.get_yticks(), signal.value_annotation.ticks)
            assert [
                text.get_text() for text in current_ax.get_yticklabels()
            ] == list(signal.value_annotation.ticklabels)
            assert np.allclose(current_ax.get_xticks(), signal.axis_annotation.ticks)
        plt.close(fig)

    def test_chrom_with_fraction_log_all_modes(self):
        """Real-world repro: Chrom (mode 1 + ax_size (16, 5)) with a fraction log."""
        from dvrazer.concrete.chromatography import Chrom, ChromLog, ChromSig

        def make_chrom_signal(name, axis, values):
            return ChromSig.from_data(
                data=pd.DataFrame({"axis": axis, "value": values}),
                name=name,
                axis_name="Time",
                axis_unit="min",
                value_name="Absorbance",
                value_unit="mAU",
            )

        def make_chrom_log(name, axis, values):
            return ChromLog.from_data(
                data=pd.DataFrame({"axis": axis, "value": values}),
                name=name,
                axis_name="Time",
                axis_unit="min",
                value_name="Fraction",
                value_unit=None,
            )

        chrom = Chrom.from_similar_signals(
            [
                make_chrom_signal("UV", [0.0, 1.0, 2.0], [1.0, 2.0, 3.0]),
                make_chrom_log("Fractions", [0.0, 1.0, 2.0], [1.0, 0.0, 1.0]),
            ],
            name="chrom",
        )
        assert chrom.plot_args.mode == 1
        assert chrom.plot_args.ax_size == (16, 5)
        chrom.set_default_annotations()

        # mode 2: the fraction subplot must not need value ticks
        fig, axes = chrom.plot(mode=2)
        assert chrom.plot_args.margin is not None  # was auto-measured for mode 2
        flat_axes = flatten(axes)
        assert len(flat_axes) >= len(chrom.visible_signal_names)
        uv_ax = flat_axes[chrom.visible_signal_names.index("UV")]
        fractions_ax = flat_axes[chrom.visible_signal_names.index("Fractions")]
        assert np.allclose(uv_ax.get_yticks(), chrom["UV"].value_annotation.ticks)
        assert list(fractions_ax.get_yticks()) == []
        assert fractions_ax.get_ylim() == (0.0, 1.0)
        plt.close(fig)

        # smoke: the other modes keep working on the same mixed collection
        fig, ax = chrom.plot(mode=0)
        assert isinstance(ax, plt.Axes)
        plt.close(fig)
        fig, axes = chrom.plot(mode=1)
        assert isinstance(axes, list) and len(axes) == 1  # one continuous signal
        plt.close(fig)
