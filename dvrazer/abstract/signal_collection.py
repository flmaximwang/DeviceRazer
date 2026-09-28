"""
``dvrazer.abstract.signal_collection`` --- 信号集合基类
==========================================================================

:class:`SignalCollection` 是容纳多个信号对象的容器基类。

主要功能:
- 字典式访问: ``collection["name"]``
- 信号增删改查: ``append``, ``remove_signal``, ``rename_signal``
- 批量导出: ``to_folder``
- 集合合并: ``merge``

SignalCollection 是 ``Signal1DCollection`` 和 ``ImpedanceSpectrumCollection``
等具体集合类的基类。
"""

import os, time, warnings
from dataclasses import dataclass, field
from pathlib import Path
from .signal import Signal, DescAnno
from .display import SignalPlotArgs


@dataclass
class SignalCollection:
    """
    A SignalCollection contains multiple signals and is designed to
    easily compare and visualize them.

    - Dimensions of signals in a signal collection must be the same.
    - Signals in a collection is stored by a dictionary, you can find every signal with its name like SignalCollection[signal_name]

    Properties
    ----------
    signals: list[Signal]
        A dictionary of signals in the collection, with signal names as keys.
    name: str
        The name of the signal collection.
    plot_args: PlotArgs
        The arguments for plotting the signal collection.
    """

    signals: list[Signal] = None
    signal_type: type = Signal
    visible_signal_names: list[str] = None
    name: str = None
    description_annotations: list[DescAnno] = None
    plot_args: SignalPlotArgs = None
    __index_cache__: dict = None

    @property
    def signal_names(self):
        return [signal.name for signal in self.signals]

    @staticmethod
    def merge(
        signal_collections: list["SignalCollection"], name="Merged_signal_collection"
    ) -> "SignalCollection":
        signals = []
        for signal_collection in signal_collections:
            for signal in signal_collection.signals:
                signals.append(signal)
        return SignalCollection(signals, name=name)

    def keys(self):
        return [signal.name for signal in self.signals]

    def _cache_index(self):
        keys = self.keys()
        self.__index_cache__ = {key: i for i, key in enumerate(keys)}

    def index(self, signal_name: str):
        if (
            not hasattr(self, "__index_cache__")
            or self.__index_cache__ is None
            or signal_name not in self.__index_cache__
        ):
            self._cache_index()
        if signal_name not in self.__index_cache__:
            raise KeyError(
                f"Signal name {signal_name} does not exist in the collection"
            )
        return self.__index_cache__[signal_name]

    def __contains__(self, signal_name: str):
        try:
            self.index(signal_name)
            return True
        except KeyError:
            return False

    def __getitem__(self, signal_name: str):
        signal_index = self.index(signal_name)
        return self.signals[signal_index]

    def __setitem__(self, signal_name: str, signal: Signal):
        try:
            signal_index = self.index(signal_name)
            self.signals[signal_index] = signal
            signal.name = signal_name
        except KeyError:
            signal_index = len(self.signals)
            self.signals.append(signal)
            signal.name = signal_name

    def __delitem__(self, signal_name: str):
        signal_index = self.index(signal_name)
        del self.signals[signal_index]
        del self.__index_cache__[signal_name]

    def append(self, signal: Signal) -> None:
        keys = self.keys()
        if signal.name in keys:
            raise KeyError(
                f"Signal name {signal.name} already exists in the collection"
            )
        self.signals.append(signal)
        self._cache_index()

    def remove_signal(self, signal_name: str) -> None:
        signal_index = self.index(signal_name)
        del self.signals[signal_index]
        try:
            self.visible_signal_names.remove(signal_name)
        except ValueError:
            pass
        self._cache_index()

    def rename_signal(self, old_signal_name, new_signal_name):
        signal = self[old_signal_name]
        signal.name = new_signal_name
        self._cache_index()
        try:
            old_idx = self.visible_signal_names.index(old_signal_name)
            self.visible_signal_names.remove(old_signal_name)
            self.visible_signal_names.insert(old_idx, new_signal_name)
        except ValueError:
            self.visible_signal_names.append(new_signal_name)

    def to_folder(self, directory: str | Path):
        """
        Export the collection to `root_directory/self.name`

        Parameters
        ----------
        mode : str
            "append", "write" or "replace"
        """
        directory = Path(directory)
        time_stamp = time.strftime("%Y%m%d_%H%M%S")

        if directory.exists():
            directory = directory.with_name(f"{directory.name}_{time_stamp}")
            warnings.warn(
                f"Directory {directory} already exists. Renamed to {directory.name}."
            )
        directory.mkdir(parents=True)
        for signal in self.signals:
            if "/" in signal.name:
                warnings.warn(
                    f"Signal name {signal.name} contains '/', which is not allowed in file names. They are replaced with '_'."
                )
                self.rename_signal(signal.name, signal.name.replace("/", "_"))
        for signal in self.signals:
            signal.to_csv(directory / (signal.name + ".csv"))

    def __len__(self):
        return len(self.signals)
