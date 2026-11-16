import json
import re

from decimal import Decimal, InvalidOperation

from app.models import ProductInput, GeneratedContent, Characteristic


NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")

def build_characteristics(product: ProductInput) -> list[Characteristic]:

    characteristics = []

    for name, value in product.specs.items():
        characteristics.append(
            Characteristic(
                name=name,
                value=str(value)
            )
        )

    if not characteristics:
        characteristics.append(
            Characteristic(
                name="Технические характеристики",
                value="данных нет"
            )
        )

    return characteristics


def extract_numbers(text: str) -> list[tuple[str, Decimal]]:

    result = []

    for number in NUMBER_PATTERN.findall(text):
        try:
            normalized = Decimal(
                number.replace(",", ".")
            ).normalize()

            result.append((number, normalized))

        except InvalidOperation:
            continue

    return result


def find_unsupported_numbers(product: ProductInput, generated: GeneratedContent) -> list[str]:

    source_text = json.dumps(
        product.model_dump(mode="json"),
        ensure_ascii=False
    )

    allowed_numbers = {
        normalized
        for _, normalized in extract_numbers(source_text)
    }

    generated_text = "\n".join([
        generated.seo_title,
        generated.seo_description,
        generated.commercial_block,
        *generated.search_queries
    ])

    unsupported = []

    for original, normalized in extract_numbers(generated_text):
        if normalized not in allowed_numbers:
            unsupported.append(original)

    return list(dict.fromkeys(unsupported))

def has_sufficient_data_to_generate(product: ProductInput) -> bool:

    has_description = bool(
        product.description
        and len(product.description.strip()) >= 30
    )

    has_enough_specs = len(product.specs) >= 2

    return has_description or has_enough_specs


def find_missing_data(product: ProductInput) -> list[str]:

    missing = []

    if not product.manufacturer:
        missing.append("Производитель")

    if not product.description:
        missing.append(
            "Описание назначения или фрагмент технического паспорта"
        )

    if not product.specs:
        missing.append("Технические характеристики")

    return missing