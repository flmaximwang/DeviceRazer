from dvrazer.instruments.ThermoFisher.nanodrop2000 import (
    Nanodrop2000Workbook,
)

if __name__ == "__main__":
    protein_a280 = Nanodrop2000Workbook.from_tsv("example.tsv")
    protein_a280.set_default_annotations(mode="Protein A280")
    fig, ax = protein_a280.plot()
