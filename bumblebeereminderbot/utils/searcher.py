from typing import Sequence, Callable

def searcher(
    iterable: Sequence[object],
    search_term: str,
    fields: list[str | Callable[[object], str]] | None = None,
    match_type: str = "contains",
    case_sensitive: bool = False
) -> list[int]:
    """
    Универсальная функция поиска по элементам итератора с возможностью гибкой настройки полей поиска,
    типа сопоставления и чувствительности к регистру.

    :param iterable: Список или последовательность объектов для поиска.
    :param search_term: Поисковый запрос для сопоставления.
    :param fields: Список полей для поиска. Это могут быть строки (имена атрибутов объектов или ключи словаря)
                   или функции для извлечения значений. Если не указано, поиск будет производиться по всей строковой
                   представимости объекта.
    :param match_type: Тип сопоставления. Возможные значения: 'contains', 'exact', 'startswith', 'endswith'.
    :param case_sensitive: Учитывать ли регистр при поиске. По умолчанию False.

    :return: Список индексов элементов, в которых найдено совпадение с поисковым запросом.
    """
    # Приведение поискового запроса к нужному регистру
    search_term = search_term if case_sensitive else search_term.lower()

    # Вспомогательная функция для приведения значений к нужному регистру
    def normalize_value(value: str) -> str:
        return value if case_sensitive else value.lower()

    # Определение функции для сравнения на основе типа совпадения
    def is_match(value: str) -> bool:
        match match_type:
            case "exact":      return search_term == value
            case "startswith": return value.startswith(search_term)
            case "endswith":   return value.endswith(search_term)
            case "contains":   return search_term in value
            case _:            raise ValueError(f"Неверный тип сопоставления: {match_type}")

    # Список для хранения индексов совпавших элементов
    matching_indices = []

    # Перебор элементов итератора
    for index, item in enumerate(iterable):
        # Если указаны конкретные поля для поиска
        if fields:
            for field in fields:
                # Если поле является строкой, ищем в атрибуте объекта или ключе словаря
                if isinstance(field, str):
                    value = str(getattr(item, field, item.get(field, ""))) if isinstance(item, dict) else str(getattr(item, field, ""))
                # Если поле - вызываемая функция, используем её для получения значения
                elif callable(field):
                    value = str(field(item))
                else:
                    continue  # Пропустить, если не удалось обработать поле
                
                # Сопоставляем значение и добавляем индекс при совпадении
                if is_match(normalize_value(value)):
                    matching_indices.append(index)
                    break
        else:
            # Если поля не указаны, искать по строковому представлению всего объекта
            value = str(item)
            if is_match(normalize_value(value)):
                matching_indices.append(index)

    return matching_indices