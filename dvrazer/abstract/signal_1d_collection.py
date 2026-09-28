"""
``dvrazer.abstract.signal_1d_collection`` --- 1D 信号集合
=============================================================================

该模块实现了 :class:`SignalCollection` 的一维信号集合子类:

- :class:`Signal1DCollection` : 容纳多个 ``Signal1D``, 支持:
  - ``from_folder`` / ``from_similar_signals`` : 便捷构造器
  - ``align_axes`` / ``align_values`` : 对齐坐标轴范围
  - ``plot`` : 三种绘图模式 (0=单图多线, 1=多轴对比, 2=分面绘图)
  - ``set_default_annotations`` : 自动推断各信号的范围和刻度

- :class:`ContinuousSignal1DCollection` : 只容纳 ``ContinuousSignal1D``,
  增加了 ``average_similar_signals`` 按名称分组求平均。
"""

from typing import Callable, Iterable, Literal, overload
from dataclasses import dataclass, field
from copy import deepcopy
from pathlib import Path
import numpy as np
import pandas as pd
from .signal import ContDescAnno, DiscDescAnno
from .signal_collection import SignalCollection
from .signal_1d import Signal1D, ContinuousSignal1D
from .display import Signal1DPlotArgs, _DEFAULT_MARGIN_CM
import matplotlib.pyplot as plt


@dataclass
class Signal1DCollection(SignalCollection):

    signal_type: type = Signal1D
    signals: list[Signal1D] = field(default_factory=list)
    plot_args: Signal1DPlotArgs = field(default_factory=Signal1DPlotArgs)
    # display_modes = ["main_signal_axis", "all_axis", "separate", "denoted_axis"]

    # ==================== Properties for axis description ====================

    @property
    def axis_annotation(self):
        axis_annotation: ContDescAnno = self.description_annotations[0]
        return axis_annotation

    # ==================== Properties for value description ====================

    @property
    def value_annotation(self):
        return self.description_annotations[1]

    @value_annotation.setter
    def value_annotation(self, new_value_description):
        self.description_annotations[1] = new_value_description

    # ============================ Constructors ============================

    @classmethod
    def from_similar_signals(
        cls,
        signals: list[Signal1D],
        name="Untitled",
        signal_names: list[str] | None = None,
    ):
        """
        Quickly create a Signal1DCollection from a list of similar Signal1D.
        Similar signals are defined as the signals sharing the same axis and value annotations.
        The axis and value annotations of the collection will be inherited from the first signal in the list.

        Parameters
        ----------
        signals : list[Signal1D]
            The signals to be added to the collection. They are deep-copied
            before being added, so modifying the signals or their annotations
            in the collection will NOT affect the original signals.
        name : str
            The name of the collection.
        signal_names : list[str], optional
            If given, rename the copied signals accordingly.
            Must have the same length as *signals*.
        """

        axis_annotation = deepcopy(signals[0].axis_annotation)
        value_annotation = deepcopy(signals[0].value_annotation)

        copied_signals = [deepcopy(signal) for signal in signals]
        if signal_names is not None:
            if len(signal_names) != len(copied_signals):
                raise ValueError(
                    f"The length of signal_names ({len(signal_names)}) should be the same as "
                    f"the number of signals ({len(copied_signals)})."
                )
            for signal, signal_name in zip(copied_signals, signal_names):
                signal.name = signal_name

        result = cls(
            signals=copied_signals,
            description_annotations=[axis_annotation, value_annotation],
            visible_signal_names=[signal.name for signal in copied_signals],
            name=name,
        )
        return result

    @classmethod
    def merge(
        cls,
        signal_collections: list["Signal1DCollection"],
        name="Merged Signal1DCollection",
        signal_renaming=True,
    ) -> "Signal1DCollection":
        signals: list[Signal1D] = []
        signal_names: list[str] = []
        for signal_collection in signal_collections:
            for signal in signal_collection.signals:
                if signal_renaming:
                    signal_names.append(f"{signal_collection.name}_{signal.name}")
                else:
                    signal_names.append(signal.name)
                signals.append(signal)
        return cls.from_similar_signals(signals, name=name, signal_names=signal_names)

    def extend_signals(self, new_signals: list[Signal1D]) -> None:
        for signal in new_signals:
            if signal.name in self.signal_names:
                raise ValueError(
                    f"Signal name {signal.name} already exists in the collection"
                )
            self.signals.append(signal)
            self.visible_signal_names.append(signal.name)

    # ============================ Aligner ============================

    def align_axes(self, *axis_limit) -> None:
        """
        Align the axis limits of all signals in the collection to the same axis limits.
        """
        for signal in self.signals:
            signal.axis_annotation.limit = [*axis_limit]
        self.axis_annotation.limit = [*axis_limit]

    def align_values(self, signal_names: list[str], *value_limit) -> None:
        """
        Align the value limits of selected signals in the collection to the same value limits.
        """
        if not signal_names:
            # Align values for all continuous signals
            signal_names = []
            for signal in self.signals:
                if isinstance(signal, ContinuousSignal1D):
                    signal_names.append(signal.name)
        # Align selected signals
        for signal_name in signal_names:
            signal_value_annotation: ContDescAnno = self[signal_name].value_annotation
            signal_value_annotation.limit = [*value_limit]
        value_annotation: ContDescAnno = self.value_annotation
        value_annotation.limit = [*value_limit]

    @classmethod
    def from_folder(cls, folder: str | Path, **kwargs):
        """
        Import multiple .csv files from one folder
        """
        folder = Path(folder)
        signals = []
        for file in sorted(folder.glob("*.csv")):
            signal = cls.signal_type.from_csv(file, **kwargs)
            signals.append(signal)
        result = cls.from_similar_signals(signals)
        result.name = folder.name
        return result

    # ==================== Fixed-size Axes helper ====================

    @overload
    def _make_axes(
        self, nrows: Literal[1] = 1, ncols: Literal[1] = 1
    ) -> tuple[plt.Figure, plt.Axes]: ...

    @overload
    def _make_axes(
        self, nrows: int, ncols: int
    ) -> tuple[plt.Figure, list[list[plt.Axes]]]: ...

    def _make_axes(self, nrows=1, ncols=1):
        """
        Create a Figure and Axes with a fixed data-area size (*ax_size*).

        When ``self.plot_args.ax_size`` is set, the Axes data area (between
        spines, not including labels, ticks, or legend) is exactly *ax_size*
        **cm**.  The Figure is sized to accommodate the data area plus margins
        (``plot_args.margin``, in cm), and the Axes position is set
        explicitly — **tight_layout is NOT called**, so the data area
        dimensions are guaranteed identical across plots regardless of legend
        width or tick-label length.

        When ``ax_size`` is ``None``, falls back to :func:`plt.subplots` with
        default sizing (backward-compatible).

        Parameters
        ----------
        nrows, ncols : int
            Grid dimensions.

        Returns
        -------
        ``(fig, ax)`` for 1\u00d71,
        ``(fig, axes_2d)`` for larger grids.
        ``axes_2d`` is ``list[list[plt.Axes]]``.
        """
        ax_size = self.plot_args.ax_size
        if ax_size is None:
            fig, a = plt.subplots(nrows, ncols)
            if nrows == 1 and ncols == 1:
                return fig, a
            # Normalise to list[list[Axes]]
            if nrows == 1:
                return fig, [list(a)]
            if ncols == 1:
                return fig, [[ax] for ax in a]
            return fig, a.tolist()

        # ---- fixed-size layout ------------------------------------------------
        # matplotlib uses inches internally; convert ax_size from cm.
        margin = self.plot_args.margin
        if margin is None:
            raise RuntimeError(
                "plot_args.margin is None — call plot() to auto-measure it, "
                "or set plot_args.margin explicitly"
            )
        aw = ax_size[0] / 2.54
        ah = ax_size[1] / 2.54

        ml, mr, mb, mt = margin  # cm
        ml, mr, mb, mt = ml / 2.54, mr / 2.54, mb / 2.54, mt / 2.54  # → inches

        fig_w = aw * ncols + ml + mr
        fig_h = ah * nrows + mb + mt

        fig = plt.figure(figsize=(fig_w, fig_h))

        axes_2d = []
        for row in range(nrows):
            row_axes = []
            for col in range(ncols):
                left = (ml + col * aw) / fig_w
                bottom = (mb + (nrows - 1 - row) * ah) / fig_h
                row_axes.append(
                    fig.add_axes(
                        (
                            left,
                            bottom,
                            aw / fig_w,
                            ah / fig_h,
                        )
                    )
                )
            axes_2d.append(row_axes)

        if nrows == 1 and ncols == 1:
            return fig, axes_2d[0][0]
        return fig, axes_2d

    # ==================== Auto-measured margins ====================

    def _auto_measure_margins(self, **kwargs) -> None:
        """Draw a tentative figure, measure the label extents, and store the
        measured margins (cm) into ``plot_args.margin``.

        Called when ``plot_args.margin`` is ``None`` (the default): the
        fixed-size layout needs margins before the labels exist, so we
        first build with the default constants, measure how much space
        the labels really take, then rebuild with the measured values.
        The measured margins are cached in ``plot_args.margin``, so only
        the first :meth:`plot` call pays for the extra draw.
        """
        self.plot_args.margin = _DEFAULT_MARGIN_CM
        if self.plot_args.mode == 0:
            fig, _ = self.plot_with_collection_annotations(**kwargs)
        elif self.plot_args.mode == 1:
            fig, _ = self.plot_with_all_annotations(
                axis_shift=self.plot_args.axis_shift, **kwargs
            )
        elif self.plot_args.mode == 2:
            fig, _ = self.plot_separately(**kwargs)
        else:
            raise Exception("Unknown display mode")
        fig.canvas.draw()
        measured = self._measure_label_margins(fig)
        plt.close(fig)
        self.plot_args.margin = measured

    @staticmethod
    def _measure_label_margins(fig) -> tuple[float, float, float, float]:
        """Measure the space (cm) labels need around each Axes of *fig*.

        Returns ``(left, right, bottom, top)`` margins such that no label
        (tick labels, axis labels, titles, legends, shifted twin spines)
        sticks out of the figure, plus a small padding.  Requires the
        figure to be drawn already.
        """
        pad_in = 0.1  # inches of breathing room
        dpi = fig.dpi
        overhang = {"left": 0.0, "right": 0.0, "bottom": 0.0, "top": 0.0}
        for ax in fig.axes:
            if not ax.get_visible():
                continue
            ax_bb = ax.get_window_extent()
            artists = [ax.xaxis.label, ax.yaxis.label, ax.title]
            artists += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
            if ax.legend_ is not None:
                artists.append(ax.legend_)
            for art in artists:
                try:
                    bb = art.get_window_extent()
                except Exception:
                    continue
                if bb.width == 0 and bb.height == 0:
                    continue
                overhang["left"] = max(overhang["left"], max(0.0, ax_bb.x0 - bb.x0))
                overhang["right"] = max(overhang["right"], max(0.0, bb.x1 - ax_bb.x1))
                overhang["bottom"] = max(overhang["bottom"], max(0.0, ax_bb.y0 - bb.y0))
                overhang["top"] = max(overhang["top"], max(0.0, bb.y1 - ax_bb.y1))
        return (
            (overhang["left"] / dpi + pad_in) * 2.54,
            (overhang["right"] / dpi + pad_in) * 2.54,
            (overhang["bottom"] / dpi + pad_in) * 2.54,
            (overhang["top"] / dpi + pad_in) * 2.54,
        )

    def plot_with_collection_annotations(self, **kwargs) -> tuple[plt.Figure, plt.Axes]:

        fig, ax = self._make_axes(1, 1)
        self.plot_with_collection_annotations_at(ax, **kwargs)
        if self.plot_args.ax_size is None:
            fig.tight_layout()

        return fig, ax

    def plot_with_collection_annotations_at(self, ax: plt.Axes, **kwargs):

        cmap = self.plot_args.cmap
        cmap_limit = self.plot_args.cmap_limit
        legend_cols = self.plot_args.legend_cols
        legend_bbox_to_anchor = self.plot_args.legend_bbox_to_anchor
        legend_loc = self.plot_args.legend_loc

        handles = []

        if cmap is None:
            for i, signal_name in enumerate(self.visible_signal_names):
                signal: Signal1D = self[signal_name]
                handles.append(signal.plot_at(ax, color=f"C{i}", **kwargs))
        elif isinstance(cmap, Callable):
            my_len = len(self.visible_signal_names)
            if my_len > 1:
                for i, signal_name in enumerate(self.visible_signal_names):
                    signal = self[signal_name]
                    handles.append(
                        signal.plot_at(
                            ax,
                            color=cmap(
                                i / (my_len - 1) * (cmap_limit[1] - cmap_limit[0])
                                + cmap_limit[0]
                            ),
                            **kwargs,
                        )
                    )
            else:
                signal = self[self.visible_signal_names[0]]
                handles.append(signal.plot_at(ax, color=cmap(1.0), **kwargs))
        elif isinstance(cmap, Iterable):
            if len(cmap) != len(self.visible_signal_names):
                raise ValueError(
                    "The length of colormap should be the same as the number of visible signals"
                    f" (expected {len(self.visible_signal_names)}, got {len(cmap)})"
                )
            for i, signal_name in enumerate(self.visible_signal_names):
                signal = self[signal_name]
                handles.append(signal.plot_at(ax, color=cmap[i], **kwargs))
        else:
            raise ValueError("Invalid colormap")
        xticks = self.axis_annotation.ticks
        xticklabels = self.axis_annotation.ticklabels
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)
        minor_xticks = self.axis_annotation.ticks_minor
        if minor_xticks is not None and len(minor_xticks) > 0:
            ax.set_xticks(minor_xticks, minor=True)
        if isinstance(self.value_annotation, ContDescAnno):
            yticks = self.value_annotation.ticks
            yticklabels = self.value_annotation.ticklabels
            ax.set_yticks(yticks)
            ax.set_yticklabels(yticklabels)
            minor_yticks = self.value_annotation.ticks_minor
            if minor_yticks is not None and len(minor_yticks) > 0:
                ax.set_yticks(minor_yticks, minor=True)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel(self.axis_annotation.label)
        ax.set_ylabel(self.value_annotation.label)
        ax.legend(
            handles=handles,
            ncols=legend_cols,
            bbox_to_anchor=legend_bbox_to_anchor,
            loc=legend_loc,
        )
        ax.set_title(self.name)

    def plot_with_all_annotations(
        self, axis_shift, **kwargs
    ) -> tuple[plt.Figure, list[plt.Axes]]:
        fig, ax = self._make_axes(1, 1)
        twins: list[plt.Axes] = []
        handles: list[plt.Line2D] = []
        legend_bbox_to_anchor = self.plot_args.legend_bbox_to_anchor
        legend_loc = self.plot_args.legend_loc

        counter = 0
        for i, signal_name in enumerate(self.visible_signal_names):
            signal = self[signal_name]
            if i > 0:  # Other signals share the same x axis
                if isinstance(signal, ContinuousSignal1D):
                    twins.append(ax.twinx())
                    twins[-1].spines.right.set_position(
                        ("axes", 1 + axis_shift * counter)
                    )
                    counter += 1
                    ax_to_plot = twins[-1]
                    handle = signal.plot_at(ax_to_plot, color=f"C{i}", **kwargs)
                else:
                    ax_to_plot = ax
                    handle = signal.plot_at(ax_to_plot, color=f"C{i}", **kwargs)
            else:  # The first signal controls the x axis
                if isinstance(signal, ContinuousSignal1D):
                    ax_to_plot = ax
                    handle = signal.plot_at(ax_to_plot, color=f"C{i}", **kwargs)
                else:
                    raise TypeError("The first signal should be a ContinuousSignal1D")
            if isinstance(signal, ContinuousSignal1D):

                ax_to_plot.tick_params(axis="y", colors=handle.get_color())
                ax_to_plot.yaxis.label.set_color(handle.get_color())
                ax_to_plot.set_ylim([0, 1])
                ax_to_plot.set_ylabel(signal.value_annotation.label)
                ax_to_plot.set_yticks(signal.value_annotation.ticks)
                ax_to_plot.set_yticklabels(signal.value_annotation.ticklabels)
                minor_yticks = signal.value_annotation.ticks_minor
                if minor_yticks is not None and len(minor_yticks) > 0:
                    ax_to_plot.set_yticks(minor_yticks, minor=True)

            handles.append(handle)

        ax.set_xlabel(self.axis_annotation.label)
        ax.set_xticks(self.axis_annotation.ticks)
        ax.set_xticklabels(self.axis_annotation.ticklabels)
        minor_xticks = self.axis_annotation.ticks_minor
        if minor_xticks is not None and len(minor_xticks) > 0:
            ax.set_xticks(minor_xticks, minor=True)
        ax.set_xlim(0, 1)
        ax.legend(handles=handles, loc=legend_loc, bbox_to_anchor=legend_bbox_to_anchor)
        ax.set_title(self.name)
        if self.plot_args.ax_size is None:
            fig.tight_layout()
            fig.subplots_adjust(right=1 - axis_shift * counter)
        return fig, [ax] + twins

    def plot_separately(self, **kwargs) -> tuple[plt.Figure, list[list[plt.Axes]]]:
        row_num = kwargs.pop("row", 0)
        col_num = kwargs.pop("col", 0)
        if row_num == 0 and col_num == 0:
            # 尽可能按照正方形进行 plot
            row_num = (
                int(np.sqrt(len(self.visible_signal_names))) + 1
                if np.sqrt(len(self.visible_signal_names)) % 1 != 0
                else int(np.sqrt(len(self.visible_signal_names)))
            )
            col_num = (
                len(self.visible_signal_names) // row_num + 1
                if len(self.visible_signal_names) % row_num != 0
                else len(self.visible_signal_names) // row_num
            )
        elif row_num == 0:
            # 按照 col_num 调整 row_num
            row_num = (
                len(self.visible_signal_names) // col_num + 1
                if len(self.visible_signal_names) % col_num != 0
                else len(self.visible_signal_names) // col_num
            )
        elif col_num == 0:
            # 按照 row_num 调整 col_num
            col_num = (
                len(self.visible_signal_names) // row_num + 1
                if len(self.visible_signal_names) % row_num != 0
                else len(self.visible_signal_names) // row_num
            )

        if row_num * col_num < len(self.visible_signal_names):
            raise ValueError(
                f"{row_num} rows and {col_num} columns are not enough to plot {len(self.visible_signal_names)} signals."
            )

        fig, axes = self._make_axes(row_num, col_num)

        for i, signal_name in enumerate(self.visible_signal_names):
            signal = self[signal_name]
            row_index = i // col_num
            col_index = i % col_num
            signal.plot_at(axes[row_index][col_index], **kwargs)
            axes[row_index][col_index].set_title(signal_name)
            axes[row_index][col_index].set_xlabel(self.axis_annotation.label)
            axes[row_index][col_index].set_ylabel(signal.value_annotation.label)
            xticks, xticklabels = (
                signal.axis_annotation.ticks,
                signal.axis_annotation.ticklabels,
            )
            axes[row_index][col_index].set_xticks(xticks)
            axes[row_index][col_index].set_xticklabels(xticklabels)
            minor_xticks = signal.axis_annotation.ticks_minor
            if minor_xticks is not None and len(minor_xticks) > 0:
                axes[row_index][col_index].set_xticks(minor_xticks, minor=True)
            yticks, yticklabels = (
                signal.value_annotation.ticks,
                signal.value_annotation.ticklabels,
            )
            axes[row_index][col_index].set_yticks(yticks)
            axes[row_index][col_index].set_yticklabels(yticklabels)
            minor_yticks = signal.value_annotation.ticks_minor
            if minor_yticks is not None and len(minor_yticks) > 0:
                axes[row_index][col_index].set_yticks(minor_yticks, minor=True)
            axes[row_index][col_index].set_xlim(0, 1)
            axes[row_index][col_index].set_ylim(0, 1)
        if self.plot_args.ax_size is None:
            fig.tight_layout()
        return fig, axes

    def plot(self, **kwargs):
        """
        mode = 0: plot with collection annotations
        mode = 1: plot with all value labels;
        mode = 2: plot separately;
        legend_cols: int, default 1, number of columns in the legend
        """
        if self.plot_args.ax_size is not None and self.plot_args.margin is None:
            self._auto_measure_margins(**kwargs)
        if self.plot_args.mode in [0, 1]:
            # Axes containing only 1 subplot
            if self.plot_args.mode == 0:
                fig, ax = self.plot_with_collection_annotations(**kwargs)
                ax.set_title(self.name)
                return fig, ax
            elif self.plot_args.mode == 1:
                axis_shift = self.plot_args.axis_shift
                fig, axes = self.plot_with_all_annotations(
                    axis_shift=axis_shift, **kwargs
                )
                axes[0].set_title(self.name)
                return fig, axes
        elif self.plot_args.mode in [2]:
            # Axes containing multiple subplots
            if self.plot_args.mode == 2:
                fig, axes = self.plot_separately(**kwargs)
                return fig, axes
        else:
            raise Exception("Unknown display mode")

    def set_default_annotations(self):
        axis_limit = None
        for signal in self.signals:
            axis_data = signal.data.iloc[:, 0]
            axis_min = min(axis_data)
            axis_max = max(axis_data)
            axis_limit = (
                (axis_min, axis_max)
                if axis_limit is None
                else (min(axis_limit[0], axis_min), max(axis_limit[1], axis_max))
            )
        self.align_axes(*axis_limit)
        ticklabel_space = (axis_limit[1] - axis_limit[0]) / 10
        if ticklabel_space == 0:
            raise ValueError("All signals have the same axis data.")
        self.axis_annotation.ticklabel_space_major = ticklabel_space
        self.axis_annotation.ticklabel_space_minor = ticklabel_space / 5
        collection_value_max = None
        collection_value_min = None
        for signal in self.signals:
            if isinstance(signal, ContinuousSignal1D):
                value_data = signal.data.iloc[:, 1]
                value_min = min(value_data)
                collection_value_min = (
                    value_min
                    if collection_value_min is None
                    else min(value_min, collection_value_min)
                )
                value_max = max(value_data)
                collection_value_max = (
                    value_max
                    if collection_value_max is None
                    else max(value_max, collection_value_max)
                )
                signal.value_annotation.limit = (value_min, value_max)
                ticklabel_space = (value_max - value_min) / 10
                if ticklabel_space == 0:
                    ticklabel_space = 1.0
                signal.value_annotation.ticklabel_space_major = ticklabel_space
                signal.value_annotation.ticklabel_space_minor = ticklabel_space / 5
        ticklabel_space = (collection_value_max - collection_value_min) / 10
        self.value_annotation.ticklabel_space_major = ticklabel_space
        self.value_annotation.ticklabel_space_minor = ticklabel_space / 5


@dataclass
class ContinuousSignal1DCollection(Signal1DCollection):
    """
    ContinuousSignal1DCollection is a collection of only ContinuousSignal1D
    """

    signal_type = ContinuousSignal1D
    signals: list[ContinuousSignal1D] = field(default_factory=list)

    @property
    def value_annotation(self) -> ContDescAnno:
        value_description: ContDescAnno = self.description_annotations[1]
        return value_description

    @value_annotation.setter
    def value_annotation(self, new_value_description: ContDescAnno):
        self.description_annotations[1] = new_value_description

    @classmethod
    def merge(
        cls,
        signal_collections: list["ContinuousSignal1DCollection"],
        name="Merged ContinuousSignal1DCollection",
    ):
        signals = []
        for signal_collection in signal_collections:
            for signal in signal_collection.signals:
                signals.append(signal)
        return cls(signals, name=name)

    def average_similar_signals(
        self, func_to_define_similarity=lambda x: x.split()[0]
    ) -> "ContinuousSignal1DCollection":
        """
        Average the signals with similar names in the collection

        Details
        -------
        - Similar names are defined as the names sharing the name.split()[0] part.
        """
        name_dict = {}
        for signal in self.signals:
            base_name = func_to_define_similarity(signal.name)
            if base_name not in name_dict:
                name_dict[base_name] = []
            name_dict[base_name].append(signal)
        new_signals = []
        new_signal_names = []
        for base_name, signal_list in name_dict.items():
            if len(signal_list) == 1:
                new_signals.append(signal_list[0])
            else:
                new_signals.append(type(self.signals[0]).average(signal_list))
            new_signal_names.append(base_name)

        result = type(self).from_similar_signals(
            new_signals, name=self.name, signal_names=new_signal_names
        )
        return result

    def set_default_annotations(self):
        axis_limit = None
        for signal in self.signals:
            axis_data = signal.data.iloc[:, 0]
            axis_min = min(axis_data)
            axis_max = max(axis_data)
            axis_limit = (
                (axis_min, axis_max)
                if axis_limit is None
                else (min(axis_limit[0], axis_min), max(axis_limit[1], axis_max))
            )
        self.align_axes(*axis_limit)
        self.axis_annotation.ticklabel_space_major = (
            axis_limit[1] - axis_limit[0]
        ) / 10

        value_limit = None
        for signal in self.signals:
            value_data = signal.data.iloc[:, 1]
            value_min = min(value_data)
            value_max = max(value_data)
            value_limit = (
                (value_min, value_max)
                if value_limit is None
                else (min(value_limit[0], value_min), max(value_limit[1], value_max))
            )
        self.align_values(self.signal_names, *value_limit)
        self.value_annotation.ticklabel_space_major = (
            value_limit[1] - value_limit[0]
        ) / 10
