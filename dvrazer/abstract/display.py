"""
``dvrazer.abstract.display`` --- 绘图参数配置
================================================================

提供预定义的绘图参数 dataclass:

- :class:`SignalPlotArgs` : 通用绘图参数 (图大小、配色方案、图例)
- :class:`Signal1DPlotArgs` : 1D 信号专用绘图参数 (+ 绘图模式)

绘图模式 (mode):
  0: 所有信号共享坐标轴, 叠加显示 (适合同量纲信号比较)
  1: 共享 x 轴, 每个信号独立 y 轴 (多轴对比, 适合不同量纲信号)
  2: 每个信号绘制在单独的子图中 (分面绘图)
"""

from typing import Callable, Iterable, Annotated
from dataclasses import dataclass
from matplotlib.colors import Colormap
from matplotlib import colormaps

#: Initial margins (cm) used for the auto-measurement first pass, and as the
#: base tuple when an individual side (margin_left etc.) is set before any
#: plot.  These are the historic inch defaults converted to cm.
_DEFAULT_MARGIN_CM: tuple[float, float, float, float] = (
    1.905,
    6.35,
    1.524,
    1.016,
)


@dataclass(slots=True)
class SignalPlotArgs:
    """General plotting parameters for signal collections.

    Parameters
    ----------
    axis_shift : float
        Normalised spacing between twin y-axis spines in mode 1.
    ax_size : tuple[float, float] | None
        Size of the Axes data area (between spines) *in centimetres*.
        When set, the Figure is sized as *ax_size* + margins for labels,
        legend, and title.  When ``None``, matplotlib default sizing is used.

        .. note::

            ``ax_size`` controls the **Axes**, not the Figure.  The Figure
            is roughly ``ax_size + (8 cm, 2.5 cm)`` for the extra space
            taken by y-labels, legend, and title.  For a ~25 × 13 cm
            Figure, try ``ax_size = (17, 10)``.
    cmap : str | Colormap | None
        Colour map for signal lines.  See :attr:`cmap` setter.
    cmap_limit : tuple[float, float]
        Value range mapped to the colour map.
    legend_cols : int
        Number of columns in the legend.
    legend_bbox_to_anchor : tuple[float, float]
        Bounding-box anchor for the legend, in Axes-normalised coordinates.
    """

    #: Normalised gap between twin y-axis spines (mode 1)
    axis_shift: float = 0.2
    #: Axes data-area size (width, height) in cm.  None → matplotlib default.
    ax_size: Annotated[tuple[float, float] | None, "cm"] = None
    _cmap: Colormap = None
    #: (min, max) for colour-map value range
    cmap_limit: tuple[float, float] = (0, 1)
    #: Number of legend columns
    legend_cols: int = 1
    #: Legend anchor in Axes-normalised coordinates (x, y)
    legend_bbox_to_anchor: tuple[float, float] = None
    legend_loc: str = "upper right"

    @property
    def cmap(self) -> Colormap:
        return self._cmap

    @cmap.setter
    def cmap(self, value: str | Colormap):
        if isinstance(value, str):
            self._cmap = colormaps.get_cmap(value)
        elif isinstance(value, Colormap) or value is None:
            self._cmap = value
        elif isinstance(value, Callable):
            self._cmap = value
        elif isinstance(value, Iterable):
            self._cmap = value
        else:
            raise ValueError(
                "cmap must be any of str, Colormap, Callable, Iterable or None"
            )


@dataclass(slots=True)
class Signal1DPlotArgs(SignalPlotArgs):
    """1D signal plotting parameters.

    Parameters
    ----------
    mode : int
        - 0 = overlaid (all signals share one pair of axes);
        - 1 = twin y-axes (share x-axis, each signal gets its own y-axis);
        - 2 = faceted (each signal in its own subplot).
    margin : float | tuple[float, float, float, float] | None
        Figure margins (in cm) around the Axes data area, used when
        ``ax_size`` is set (fixed-size layout).  ``None`` (default):
        measured automatically from the rendered labels on the first
        plot and cached here.  A single number applies to all four
        sides; a 4-tuple is ``(left, right, bottom, top)``: left holds
        the ylabel + ytick labels, right holds the legend (or twin
        y-axis labels), bottom holds the xlabel + xtick labels, top
        holds the title.  Individual sides can also be set with
        ``margin_left`` / ``margin_right`` / ``margin_bottom`` /
        ``margin_top``.
    """

    #: 0=overlaid, 1=twin y-axes, 2=faceted
    mode: int = 0
    #: Figure margins (cm): (left, right, bottom, top).  None → auto-measured
    #: on the first plot() call and stored here afterwards.
    _margin: tuple[float, float, float, float] | None = None

    @property
    def margin(self) -> tuple[float, float, float, float] | None:
        """Figure margins in **cm** around the Axes data area.

        Ordered ``(left, right, bottom, top)`` — same unit as
        :attr:`ax_size`, so the fixed-size layout stays consistent.

        ``None`` (default): the first
        :meth:`~dvrazer.abstract.signal_1d_collection.Signal1DCollection.plot`
        call draws a tentative figure, measures the space the labels
        actually need, and stores the measured margins here, so
        subsequent plots reuse them.  Assigning ``None`` forces a
        re-measurement.

        Otherwise the assigned value is used literally (labels may be
        clipped if the margins are too small): a single number applies
        to all four sides, a 4-tuple for per-side values.  Individual
        sides can be set via :attr:`margin_left` / :attr:`margin_right`
        / :attr:`margin_bottom` / :attr:`margin_top`; setting one side
        before any plot bases the others on the default constants::

            plot_args.margin = 1.0
            plot_args.margin = (1.9, 2.0, 1.5, 1.0)   # left, right, bottom, top
            plot_args.margin_right = 2.5              # only the right margin
            plot_args.margin = None                   # re-measure automatically
        """
        return self._margin

    @margin.setter
    def margin(self, value: float | tuple[float, float, float, float] | None):
        if value is None:
            self._margin = None
            return
        if isinstance(value, (int, float)):
            margins = (value, value, value, value)
        else:
            margins = tuple(value)
        if len(margins) != 4:
            raise ValueError(
                "margin must be a single number (all four sides) or a "
                f"(left, right, bottom, top) 4-tuple, got {value!r}"
            )
        if any(m < 0 for m in margins):
            raise ValueError(f"margin values must be >= 0, got {value!r}")
        self._margin = margins

    def _set_margin(self, index: int, name: str, value: float):
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")
        base = self._margin if self._margin is not None else _DEFAULT_MARGIN_CM
        margins = list(base)
        margins[index] = value
        self._margin = (margins[0], margins[1], margins[2], margins[3])

    @property
    def margin_left(self) -> float:
        """Left margin (cm): ylabel + ytick labels."""
        return (self._margin or _DEFAULT_MARGIN_CM)[0]

    @margin_left.setter
    def margin_left(self, value: float):
        self._set_margin(0, "margin_left", value)

    @property
    def margin_right(self) -> float:
        """Right margin (cm): legend / twin y-axis."""
        return (self._margin or _DEFAULT_MARGIN_CM)[1]

    @margin_right.setter
    def margin_right(self, value: float):
        self._set_margin(1, "margin_right", value)

    @property
    def margin_bottom(self) -> float:
        """Bottom margin (cm): xlabel + xtick labels."""
        return (self._margin or _DEFAULT_MARGIN_CM)[2]

    @margin_bottom.setter
    def margin_bottom(self, value: float):
        self._set_margin(2, "margin_bottom", value)

    @property
    def margin_top(self) -> float:
        """Top margin (cm): title."""
        return (self._margin or _DEFAULT_MARGIN_CM)[3]

    @margin_top.setter
    def margin_top(self, value: float):
        self._set_margin(3, "margin_top", value)
