"""
``dvrazer.utils.transform_utils`` --- 数据缩放工具
======================================================================

提供数据线性变换函数, 用于将实际数据值缩放到绘图坐标系统。

主要函数:
- :func:`rescale` : 通用线性缩放 (old_range → new_range)
- :func:`rescale_to_0_1` : 缩放到 [0, 1] 区间
- :func:`extend_range` : 按比例扩展范围
"""

import numpy as np

def rescale(data, old_start, old_end, new_start, new_end):
    """
    Rescale data with linear transformation, old start will be mapped to new start, old end will be mapped to new end
    """
    return (data - old_start) / (old_end - old_start) * (new_end - new_start) + new_start

def rescale_to_0_1(data, old_start, old_end):
    """
    Rescale data with linear transformation, old start will be mapped to 0, old end will be mapped to 1
    """
    return rescale(data, old_start, old_end, 0, 1)

def extend_range(range, ratio):
    """
    Extend the range by ratio
    """
    center = (range[0] + range[1]) / 2
    return (center - ratio * (center - range[0]), center + ratio * (range[1] - center))