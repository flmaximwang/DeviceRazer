from dvrazer.instruments.ThermoFisher.nanodrop2000 import (
    Nanodrop2000Workbook,
)


def main():
    uv_vis = Nanodrop2000Workbook.from_tsv("example.tsv")
    uv_vis = uv_vis.average_similar_signals()
    uv_vis.set_default_annotations(mode="UV-Vis")
    uv_vis.align_values(uv_vis.signal_names, 0, 1)
    uv_vis.value_annotation.ticklabel_space = (0.2, 0.04)
    fig, ax = uv_vis.plot()
    uv_vis["example"].plot_peak_at(ax, 400, 420)


if __name__ == "__main__":
    main()
