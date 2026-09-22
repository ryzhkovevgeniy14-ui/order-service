class InvalidOrderError(ValueError):
    """Нарушение инварианта заказа (невалидные поля)."""


class InvalidStatusTransitionError(Exception):
    """Недопустимый переход статуса заказа."""


class OrderNotFoundError(Exception):
    """Заказ не найден."""
