"""
``dvrazer.utils.path_utils`` --- 路径处理
=============================================================

提供从文件路径提取名称的工具函数。

:func:`get_name_from_path` : 从文件路径提取不含扩展名的名称
:func:`get_name_from_basename` : 从文件名提取不含扩展名的名称
"""

import os

def get_name_from_path(file_path, extension=True):
    basename = os.path.basename(file_path)
    if extension:
        return ".".join(basename.split('.')[:-1])
    else:
        return basename

def get_name_from_basename(basename, extension=True):
    if extension:
        return ".".join(basename.split('.')[:-1])
    else:
        return basename