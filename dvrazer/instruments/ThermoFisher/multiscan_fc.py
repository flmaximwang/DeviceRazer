"""
``instruments.ThermoFisher.multiscan_fc`` --- Thermo Fisher Multiskan FC 数据解析
==================================================================================

解析 Multiskan FC 酶标仪导出的 .txt 文件。

:class:`MultiWellPlateFC` 继承自 :class:`MultiWellPlate`:
- 在 .txt 文件中查找 1-12 列的标题行
- 读取后续的 tab 分隔数据
- 自动检测板型

使用示例::

    from dvrazer.instruments import MultiWellPlateFC

    plate = MultiWellPlateFC.from_exported_file("plate_data.txt")
    value = plate["A", 1]
"""

from ...concrete.multi_well_plates import MultiWellPlate
import io
import pandas as pd


class MultiWellPlateFC(MultiWellPlate):

    @staticmethod
    def from_exported_file(txt_path, name="Default Multi-Scan Fluorescence Collection"):
        with open(txt_path, "r") as f:
            flag = False
            data_txt = ""
            for line in f:
                if not flag and "	1	2	3	4	5	6	7	8	9	10	11	12" in line:
                    flag = True
                if flag:
                    data_txt += line
        my_df = pd.read_csv(io.StringIO(data_txt), sep="\t", index_col=0)

        return MultiWellPlateFC(data=my_df, name=name)
