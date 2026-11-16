
import json

from openai import AsyncOpenAI, DefaultAsyncHttpx2Client, APIError, APIConnectionError, APITimeoutError, APIStatusError, AuthenticationError, RateLimitError

from pydantic import ValidationError

from app.settings import settings
from app.models import ProductInput, GeneratedContent

from app.services.promt import SYSTEM_PROMPT, build_user_prompt


class LLMServiceError(Exception):
    pass


def create_client() -> AsyncOpenAI:

    client_options = {
        "api_key": settings.openrouter_api_key,
        "base_url": "https://openrouter.ai/api/v1",
        "timeout": 60.0,
        "max_retries": 1,
        "default_headers": {
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_app_name,
            "X-OpenRouter-Experimental-Metadata": "enabled",
            "X-OpenRouter-Metadata": "enabled"
        }
    }

    if settings.openrouter_proxy:
        http_client = DefaultAsyncHttpx2Client(
            proxy=settings.openrouter_proxy,
            timeout=60.0
        )

        client_options["http_client"] = http_client

    return AsyncOpenAI(**client_options)


def extract_api_error(error: APIStatusError) -> str:
    try:
        body = error.response.json()
    except Exception:
        body = getattr(error, "body", None)

    if not isinstance(body, dict):
        return f"HTTP {error.status_code}: {error}"

    api_error = body.get("error", body)

    if not isinstance(api_error, dict):
        return f"HTTP {error.status_code}: {body}"

    message = api_error.get(
        "message",
        "Неизвестная ошибка OpenRouter"
    )

    metadata = api_error.get("metadata")

    if metadata:
        message += (
            "\nДополнительные сведения: "
            + json.dumps(metadata, ensure_ascii=False)
        )

    error_type = api_error.get("error_type")

    if error_type:
        message += f"\nТип ошибки: {error_type}"

    return f"HTTP {error.status_code}: {message}"


async def generate_content(product: ProductInput) -> GeneratedContent:

    if not settings.openrouter_api_key:
        raise LLMServiceError(
            "Не указан OPENROUTER_API_KEY в файле .env"
        )

    client = create_client()

    try:
        response = await client.chat.completions.create(
            model=settings.openrouter_model,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": build_user_prompt(product)
                }
            ],

            response_format={
                "type": "json_object"
            },

            temperature=0.4,
            max_tokens=3000
        )

    except AuthenticationError as error:
        raise LLMServiceError(
            "Неверный или недействительный API-ключ OpenRouter."
        ) from error

    except RateLimitError as error:
        raise LLMServiceError(
            f"Превышен лимит запросов OpenRouter: {error}"
        ) from error

    except APITimeoutError as error:
        raise LLMServiceError(
            f"Превышено время ожидания ответа: {error}"
        ) from error

    except APIConnectionError as error:
        raise LLMServiceError(
            f"Ошибка соединения с OpenRouter. "
            f"Проверь прокси и сетевое подключение: {error}"
        ) from error

    except APIStatusError as error:
        raise LLMServiceError(
            extract_api_error(error)
        ) from error

    except APIError as error:
        raise LLMServiceError(
            f"Ошибка OpenAI SDK: {error}"
        ) from error

    finally:
        await client.close()

    if not response.choices:
        raise LLMServiceError(
            "OpenRouter вернул пустой ответ."
        )

    content = response.choices[0].message.content

    if not content:
        raise LLMServiceError(
            "Модель не вернула текстовый ответ."
        )

    try:
        parsed_content = json.loads(content)

    except json.JSONDecodeError as error:
        raise LLMServiceError(
            "Модель вернула некорректный JSON."
        ) from error

    try:
        return GeneratedContent.model_validate(parsed_content)

    except ValidationError as error:
        details = []

        for item in error.errors():
            field = ".".join(
                str(part) for part in item["loc"]
            )

            details.append(
                f"{field}: {item['msg']}"
            )

        raise LLMServiceError(
            "Ответ модели не соответствует требованиям: "
            + "; ".join(details)) \
            from error
