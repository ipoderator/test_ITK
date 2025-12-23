from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    """базовая схема для item с общими полями"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="название элемента (от 1 до 255 символов)"
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="описание элемента (максимум 1000 символов)"
    )


class ItemCreate(ItemBase):
    """схема для создания нового item"""
    pass


class ItemUpdate(BaseModel):
    """схема для обновления item (все поля опциональные)"""
    name: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="название элемента (от 1 до 255 символов)"
    )
    description: str | None = Field(
        None,
        max_length=1000,
        description="описание элемента (максимум 1000 символов)"
    )


class ItemResponse(ItemBase):
    """схема для ответа с данными item"""
    id: int

    class Config:
        from_attributes = True
