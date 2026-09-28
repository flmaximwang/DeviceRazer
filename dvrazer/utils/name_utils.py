"""
``dvrazer.utils.name_utils`` --- 名称去重
=============================================================

:func:`rename_duplicated_names` 对排序后列表中的重复名称添加 ``_1``, ``_2`` 后缀。
"""

def rename_list(counter, i, name_list):
    for j in range(1, counter+1):
        name_list[i-j] = name_list[i-j] + f"_{j}"
    return 0
    
def rename_duplicated_names(name_list):
    counter = 0
    for i in range(1, len(name_list)):
        if name_list[i] == name_list[i-1]:
            counter += 1
            if counter > 0 and i == len(name_list) - 1:
                counter = rename_list(counter, i + 1, name_list)
        else:
            if counter > 0:
                counter = rename_list(counter, i, name_list)