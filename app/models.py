from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=200,
        description="Название товара"
    )

    manufacturer: Optional[str] = None

    specs: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Технические характеристики товара"
    )

    description: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("manufacturer", "description", mode="before")
    @classmethod
    def clean_optional_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        return value

    @field_validator("specs", mode="before")
    @classmethod
    def clean_specs(cls, value):
        if not isinstance(value, dict):
            raise ValueError("Поле specs должно быть JSON-объектом")

        cleaned = {}

        for key, item in value.items():
            key = str(key).strip()

            if not key:
                continue

            if isinstance(item, str):
                item = item.strip()

            if item is None or item == "":
                continue

            cleaned[key] = item

        return cleaned


class GeneratedContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str = Field(
        description="SEO-заголовок до 70 символов"
    )

    seo_description: str = Field(
        description="SEO-описание от 800 до 1200 символов"
    )

    search_queries: list[str] = Field(
        min_length=3,
        max_length=5
    )

    commercial_block: str

    additional_missing_data: list[str] = Field(
        default_factory=list
    )

    @field_validator("seo_title", "seo_description", "commercial_block")
    @classmethod
    def clean_text(cls, value):
        return value.strip()

    @field_validator("seo_title")
    @classmethod
    def validate_seo_title_length(cls, value):
        if len(value) > 70:
            raise ValueError(
                "SEO-заголовок должен содержать не более 70 символов"
            )

        if not value:
            raise ValueError("SEO-заголовок не может быть пустым")

        return value

    @field_validator("seo_description")
    @classmethod
    def validate_seo_description_length(cls, value):
        if not 800 <= len(value) <= 1200:
            raise ValueError(
                "SEO-описание должно содержать от 800 до 1200 символов. "
                f"Получено: {len(value)}"
            )

        return value

    @field_validator("search_queries")
    @classmethod
    def clean_search_queries(cls, value):
        return [query.strip() for query in value if query.strip()]


class Characteristic(BaseModel):
    name: str
    value: str


class ProductCardResponse(BaseModel):
    product_name: str
    manufacturer: Optional[str]

    seo_title: str
    seo_description: str

    characteristics: list[Characteristic]

    search_queries: list[str]

    commercial_block: str

    missing_data: list[str]