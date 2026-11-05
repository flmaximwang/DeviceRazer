"""
``dvrazer.instruments.Cytiva`` --- Cytiva / GE Healthcare (ÄKTA) 数据解析
=========================================================================

Cytiva 于 2020 年从 GE Healthcare 收购 ÄKTA 业务线, 因此两个厂商名下的
解析器是同一份实现: 本包各模块只是重新导出 :mod:`dvrazer.instruments.GE_Heathcare`
中的类型, 两种导入路径都可用。

- :mod:`unicorn5` : Unicorn 5 (ÄKTA) 色谱 (.xls / .asc)
- :mod:`unicorn7` : Unicorn 7 (ÄKTA) 色谱 (.txt, UTF-16 LE)
- :mod:`unicorn_archive` : 旧版解析 (legacy, 不作为公开 API 导出)

公开类型可直接从本包导入::

    from dvrazer.instruments.Cytiva import Unicorn5Chrom, Unicorn7Project
    from dvrazer.instruments.Cytiva import Unicorn7Chrom     # from_txt 便捷入口
    from dvrazer.instruments import Unicorn5Chrom            # 顶层也重新导出
"""

from .unicorn5 import Unicorn5Chrom
from .unicorn7 import Unicorn7Chrom, Unicorn7Project

__all__ = [
    "Unicorn5Chrom",
    "Unicorn7Chrom",
    "Unicorn7Project",
]
