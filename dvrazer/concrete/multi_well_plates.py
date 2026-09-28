"""
``dvrazer.concrete.multi_well_plates`` --- 多孔板数据
==========================================================================

多孔板 (Microplate) 相关的具体数据类型:

- :class:`MultiWellPlate` : 单次读板数据
  - 自动检测板型 (6, 12, 24, 48, 96, 384 孔)
  - 支持标准曲线法校准测量

- :class:`MultiWellPlateSeries` : 孔板时间序列

支持的孔板布局:
  ======  =========  =========
  孔数    行标签     列标签
  ======  =========  =========
  6       A-B        1-3
  12      A-C        1-4
  24      A-D        1-6
  48      A-F        1-8
  96      A-H        1-12
  384     A-P        1-24
  ======  =========  =========
"""

from dataclasses import dataclass, field
from pathlib import Path
import scipy.stats as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from ..abstract import Matrix, MatrixSeries

PLATE_COL_NAMES = {
    6: [1, 2, 3],
    12: [1, 2, 3, 4],
    24: [1, 2, 3, 4, 5, 6],
    48: [1, 2, 3, 4, 5, 6, 7, 8],
    96: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    384: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    + [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
}

PLATE_ROW_NAMES = {
    6: ["A", "B"],
    12: ["A", "B", "C"],
    24: ["A", "B", "C", "D"],
    48: ["A", "B", "C", "D", "E", "F"],
    96: ["A", "B", "C", "D", "E", "F", "G", "H"],
    384: ["A", "B", "C", "D", "E", "F", "G", "H"]
    + ["I", "J", "K", "L", "M", "N", "O", "P"],
}


@dataclass
class MultiWellPlate(Matrix):

    type: str = None

    def __post_init__(self):
        if self.data.shape == (3, 2):
            self.type = "6-well"
            self.data.columns = [1, 2, 3]
            self.data.index = ["A", "B"]
        elif self.data.shape == (4, 3):
            self.type = "12-well"
            self.data.columns = [1, 2, 3, 4]
            self.data.index = ["A", "B", "C"]
        elif self.data.shape == (6, 4):
            self.type = "24-well"
            self.data.columns = [1, 2, 3, 4, 5, 6]
            self.data.index = ["A", "B", "C", "D"]
        elif self.data.shape == (8, 6):
            self.type = "48-well"
            self.data.columns = [1, 2, 3, 4, 5, 6, 7, 8]
            self.data.index = ["A", "B", "C", "D", "E", "F"]
        elif self.data.shape == (8, 12):
            self.type = "96-well"
            self.data.columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            self.data.index = ["A", "B", "C", "D", "E", "F", "G", "H"]
        elif self.data.shape == (16, 24):
            self.type = "384-well"
            self.data.columns = [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
            ]
            self.data.index = [
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
                "I",
                "J",
                "K",
                "L",
                "M",
                "N",
                "O",
                "P",
            ]
        else:
            raise ValueError("Unsupported multi-well plate shape")

    def __getitem__(self, key: tuple[str, int]):
        return self.data.loc[key[0], key[1]]

    def calibration_and_measurement(
        self,
        calibration_values: list[float],
        calibration_markers: list[tuple[str, int]],
        measurement_markers: list[tuple[str, int]],
        xlabel: str,
        ylabel: str,
        calibration_scatter_color="black",
        calibration_scatter_size=30,
        calibration_scatter_marker="+",
        calibration_line_color="red",
        calibration_line_width=1,
        measurement_scatter_color: list[str] | str = "default",
        measurement_scatter_size=30,
        measurement_scatter_marker="^",
        legend_col_num=1,
    ):
        """
        Perform a linear calibration using known wells, then estimate values for
        measurement wells from the fitted line.

        The method reads the response values stored in the current plate for all
        calibration wells, fits a straight line with ``scipy.stats.linregress``
        using ``calibration_values`` as the x-axis and the plate readings as the
        y-axis, and then back-calculates the x values of the measurement wells
        from the fitted model.

        A scatter plot of calibration points and a fitted regression line is
        created. Measurement wells are added to the same plot either with auto-
        assigned Matplotlib cycle colors or with user-provided colors.

        Parameters
        ----------
        calibration_values : list[float]
            Known reference values used as the x-axis of the calibration curve.
            The order must match ``calibration_markers`` exactly.
        calibration_markers : list[tuple[str, int]]
            Plate well markers for the calibration points. Each marker is a
            ``(row_name, column_number)`` tuple such as ``("A", 1)``.
        measurement_markers : list[tuple[str, int]]
            Plate well markers whose values will be estimated from the fitted
            calibration curve.
        xlabel : str
            Label for the x-axis of the generated plot.
        ylabel : str
            Label for the y-axis of the generated plot.
        calibration_scatter_color : str, default="black"
            Color used for the calibration scatter points.
        calibration_scatter_size : float, default=30
            Marker size used for the calibration scatter points.
        calibration_scatter_marker : str, default="+"
            Matplotlib marker style used for the calibration scatter points.
        calibration_line_color : str, default="red"
            Color used for the fitted regression line.
        calibration_line_width : float, default=1
            Line width used for the fitted regression line.
        measurement_scatter_color : list[str] | str, default="default"
            Color specification for measurement points.

            - If set to ``"default"``, each measurement well is plotted with a
              different Matplotlib cycle color and receives a legend entry.
            - If a single color string is provided, all measurement wells are
              plotted with that color and no legend is added.
            - If a list of color strings is provided, its length must match
              ``measurement_markers`` and each point receives a legend entry.
        measurement_scatter_size : float, default=30
            Marker size used for the measurement scatter points.
        measurement_scatter_marker : str, default="^"
            Matplotlib marker style used for the measurement scatter points.
        legend_col_num : int, default=1
            Number of columns used when rendering the legend for measurement
            points that have individual labels.

        Returns
        -------
        tuple
            A 4-item tuple ``(fig, ax, result, result_table)`` where:

            - ``fig`` is the created Matplotlib figure.
            - ``ax`` is the Matplotlib axes containing the plot.
            - ``result`` is the ``LinregressResult`` returned by
              ``scipy.stats.linregress``.
            - ``result_table`` is a pandas DataFrame with columns ``Markers``,
              ``Values``, and ``Sigmas`` for the measurement wells.

        Notes
        -----
        The estimated measurement value is calculated as
        ``(measured_signal - intercept) / slope``.

        The method also prints ``result_table`` to standard output in Markdown
        table format via ``DataFrame.to_markdown()``.

        Raises
        ------
        ValueError
            If ``calibration_values`` and ``calibration_markers`` do not have
            the same length.
        ValueError
            If ``measurement_scatter_color`` is a color list whose length does
            not match the number of measurement wells.
        """

        if len(calibration_values) != len(calibration_markers):
            raise ValueError(
                "The length of calibration_index and calibration_values should be the same"
            )
        x = pd.Series(calibration_values)
        y = []
        for i in calibration_markers:
            y.append(self[i[0], i[1]])
        y = pd.Series(y)
        result = st.linregress(x, y)
        y_fitting = x.apply(lambda x: result.slope * x + result.intercept)

        fig, ax = plt.subplots(1, 1)
        ax.scatter(
            x,
            y,
            s=calibration_scatter_size,
            c=calibration_scatter_color,
            marker=calibration_scatter_marker,
        )
        ax.plot(
            x, y_fitting, c=calibration_line_color, linewidth=calibration_line_width
        )

        measurement_values = list(map(lambda x: self[x[0], x[1]], measurement_markers))
        measurement_indices = pd.Series(
            map(lambda x: (x - result.intercept) / result.slope, measurement_values)
        )
        if measurement_scatter_color == "default":
            for i, [mindex, mvalue] in enumerate(
                zip(measurement_indices, measurement_values)
            ):
                ax.scatter(
                    mindex,
                    mvalue,
                    s=measurement_scatter_size,
                    c=f"C{i}",
                    marker=measurement_scatter_marker,
                    label=f"{measurement_markers[i][0]}{measurement_markers[i][1]}",
                )
        elif isinstance(measurement_scatter_color, str):
            ax.scatter(
                measurement_indices,
                measurement_values,
                s=measurement_scatter_size,
                c=measurement_scatter_color,
                marker=measurement_scatter_marker,
            )
        else:
            if len(measurement_indices) != len(measurement_scatter_color):
                raise ValueError(
                    "The length of measurement_indices and measurement_scatter_color should be the same"
                )
            for i, [mindex, mvalue, mcolor] in enumerate(
                zip(measurement_indices, measurement_values, measurement_scatter_color)
            ):
                ax.scatter(
                    mindex,
                    mvalue,
                    s=measurement_scatter_size,
                    c=mcolor,
                    marker=measurement_scatter_marker,
                    label=f"{measurement_markers[i][0]}{measurement_markers[i][1]}",
                )
            ax.legend(ncol=legend_col_num)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        result_table = pd.DataFrame(columns=["Markers", "Values", "Sigmas"])
        result_table["Markers"] = [i[0] + str(i[1]) for i in measurement_markers]
        result_table["Values"] = measurement_indices
        result_table["Sigmas"] = np.sqrt(
            (result.intercept_stderr / result.slope) ** 2
            + (measurement_values - result.intercept) ** 2
            / result.slope**4
            * result.stderr**2
        )
        print(result_table.to_string())

        return fig, ax, result, result_table


@dataclass
class MultiWellPlateSeries(MatrixSeries):

    pass
