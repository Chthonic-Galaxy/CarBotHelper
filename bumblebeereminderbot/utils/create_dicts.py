from collections.abc import Iterable

def super_dicts_creator(d):
    """
    Создает список словарей из входного словаря, расширяя итерируемые значения по их длине.
    """
    result = []
    max_length = 1

    # Определение максимальной длины среди итерируемых значений (не строк)
    for value in d.values():
        if isinstance(value, Iterable) and not isinstance(value, str):
            max_length = max(max_length, len(value))

    # Создание результирующих словарей
    for i in range(max_length):
        item = {}
        for key, value in d.items():
            if isinstance(value, Iterable) and not isinstance(value, str):
                if i < len(value):
                    item[key] = value[i]
                else:
                    item[key] = value[-1]  # Использование последнего значения, если индекс выходит за границы
            else:
                item[key] = value
        result.append(item)

    return result
