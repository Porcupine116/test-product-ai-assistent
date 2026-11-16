from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.models import ProductInput, ProductCardResponse

from app.settings import settings

from app.services.llm_service import generate_content, LLMServiceError

from app.validators import find_missing_data, build_characteristics, find_unsupported_numbers, has_sufficient_data_to_generate


app = FastAPI(
    title="Product AI Assistant",
    description=(
        "AI-помощник для подготовки товарных карточек "
        "контрольно-измерительных приборов"
    ),
    version="1.0.0")


TEMPLATE_PATH = (Path(__file__).parent / "templates" / "index.html")


@app.get("/", include_in_schema=False)
async def get_index():
    return FileResponse(TEMPLATE_PATH)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "llm_configured": bool(settings.openrouter_api_key)
    }

@app.post("/api/generate",response_model=ProductCardResponse)
async def generate_product_card(product: ProductInput):

    if not has_sufficient_data_to_generate(product):

        missing = find_missing_data(product)

        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Недостаточно исходных данных "
                    "для подготовки полноценной товарной карточки."
                ),
                "missing_data": missing,
                "recommendation": (
                    "Добавьте описание назначения прибора "
                    "или минимум две технические характеристики."
                )
            }
        )

    try:
        generated = await generate_content(product)

    except LLMServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )

    unsupported_numbers = find_unsupported_numbers(
        product,
        generated
    )

    if unsupported_numbers:
        raise HTTPException(
            status_code=502,
            detail={
                "message": (
                    "Обнаружены числовые значения, "
                    "отсутствующие во входных данных."
                ),
                "unsupported_numbers": unsupported_numbers
            }
        )

    missing = find_missing_data(product)

    missing.extend(generated.additional_missing_data)

    missing = list(dict.fromkeys(missing))

    characteristics = build_characteristics(product)

    return ProductCardResponse(
        product_name=product.name,
        manufacturer=product.manufacturer,
        seo_title=generated.seo_title,
        seo_description=generated.seo_description,
        characteristics=characteristics,
        search_queries=generated.search_queries,
        commercial_block=generated.commercial_block,
        missing_data=missing
    )