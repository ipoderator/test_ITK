from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """Базовая схема для Item с общими полями"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Название элемента (от 1 до 255 символов)"
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Описание элемента (максимум 1000 символов)"
    )


class ItemCreate(ItemBase):
    """Схема для создания нового Item"""
    pass


class ItemUpdate(BaseModel):
    """Схема для обновления Item (все поля опциональные)"""
    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Название элемента (от 1 до 255 символов)"
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="Описание элемента (максимум 1000 символов)"
    )


class ItemResponse(ItemBase):
    """Схема для ответа с данными Item"""
    id: int

    class Config:
        from_attributes = True
