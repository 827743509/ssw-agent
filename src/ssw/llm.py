from functools import lru_cache
from langchain_openai import ChatOpenAI
from ssw.config import get_settings

settings = get_settings()

@lru_cache(maxsize=1)
def build_llm()->ChatOpenAI:
    return ChatOpenAI(
    model=settings.ssw_model,
    api_key=settings.ssw_api_key,
    base_url=settings.ssw_base_url,
    extra_body={
            "thinking": {
                "type": "disabled",
            }
    },
)