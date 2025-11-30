import re

# Списки категорий для доходов
INCOME_CATEGORIES = ["зарплата", "аванс", "пополнение", "доход", "премия"]


def parse_message(text: str):
    parts = re.split(r"\s*,\s*", text.strip())
    if len(parts) != 2:
        raise ValueError('❌ Неверный формат. Используйте: "Категория, Сумма"')

    category = parts[0].strip().lower()
    try:
        amount = float(parts[1].replace(" ", ""))
    except ValueError:
        raise ValueError("❌ Сумма должна быть числом")

    # Определяем тип операции (доход/расход)
    is_income = category in [cat.lower() for cat in INCOME_CATEGORIES]

    return category, amount, is_income


def is_income_category(category: str) -> bool:
    """Проверяет, является ли категория доходом"""
    return category.lower() in [cat.lower() for cat in INCOME_CATEGORIES]
