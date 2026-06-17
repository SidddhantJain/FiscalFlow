from pydantic import BaseModel, ConfigDict

class CategoryBase(BaseModel):
    name: str
    type: str  # INCOME, EXPENSE, INVESTMENT, SAVINGS
    icon: str | None = None
    color: str | None = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    icon: str | None = None
    color: str | None = None

class Category(CategoryBase):
    id: int
    user_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
