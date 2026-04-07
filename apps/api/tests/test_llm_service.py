"""Tests for LLM provider abstraction, factory, and service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.llm.providers.base import LLMMessage, LLMProvider, LLMResponse
from services.llm.providers.openai_provider import OpenAILLMProvider
from services.llm.providers.gemini_provider import GeminiLLMProvider
from services.llm.providers.factory import create_llm_provider
from services.llm.service import LLMService
from config.settings import Settings


def _make_messages():
    return [
        LLMMessage(role="system", content="You are a helper."),
        LLMMessage(role="user", content="Hello"),
    ]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class TestLLMMessage:
    def test_fields(self):
        m = LLMMessage(role="user", content="hi")
        assert m.role == "user"
        assert m.content == "hi"

    def test_all_roles(self):
        for role in ("system", "user", "assistant"):
            m = LLMMessage(role=role, content="")
            assert m.role == role


class TestLLMResponse:
    def test_default_usage_empty(self):
        r = LLMResponse(content="ok", model="gpt-4o-mini")
        assert r.usage == {}

    def test_usage_dict(self):
        r = LLMResponse(
            content="ok",
            model="gpt-4o-mini",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert r.usage["prompt_tokens"] == 10


# ---------------------------------------------------------------------------
# OpenAI Provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOpenAILLMProvider:
    @pytest.fixture
    def mock_openai(self):
        with patch("services.llm.providers.openai_provider.AsyncOpenAI") as mock_cls:
            client = mock_cls.return_value
            client.chat = MagicMock()
            client.chat.completions = MagicMock()

            mock_choice = MagicMock()
            mock_choice.message.content = "Hello back!"
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_response.usage = MagicMock(prompt_tokens=8, completion_tokens=3)
            client.chat.completions.create = AsyncMock(return_value=mock_response)
            yield mock_cls

    async def test_complete_returns_response(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key", model="gpt-4o-mini")
        result = await provider.complete(_make_messages())
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello back!"
        assert result.model == "gpt-4o-mini"
        assert result.usage["prompt_tokens"] == 8
        assert result.usage["completion_tokens"] == 3

    async def test_complete_passes_parameters(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key")
        await provider.complete(_make_messages(), temperature=0.3, max_tokens=100)
        call_kwargs = mock_openai.return_value.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.3
        assert call_kwargs.kwargs["max_tokens"] == 100

    async def test_complete_forwards_extra_kwargs(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key")
        await provider.complete(_make_messages(), top_p=0.9)
        call_kwargs = mock_openai.return_value.chat.completions.create.call_args
        assert call_kwargs.kwargs["top_p"] == 0.9

    async def test_complete_no_usage(self, mock_openai):
        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="x"))],
                usage=None,
            )
        )
        provider = OpenAILLMProvider(api_key="test-key")
        result = await provider.complete(_make_messages())
        assert result.usage == {}

    async def test_complete_null_content(self, mock_openai):
        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=None))],
                usage=None,
            )
        )
        provider = OpenAILLMProvider(api_key="test-key")
        result = await provider.complete(_make_messages())
        assert result.content == ""

    async def test_stream_yields_chunks(self, mock_openai):
        chunks_data = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
        ]

        class AsyncIter:
            def __init__(self, items):
                self._items = items

            def __aiter__(self):
                self._i = 0
                return self

            async def __anext__(self):
                if self._i >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._i]
                self._i += 1
                return item

        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=AsyncIter(chunks_data)
        )
        provider = OpenAILLMProvider(api_key="test-key")
        collected = []
        async for chunk in provider.stream(_make_messages()):
            collected.append(chunk)
        assert collected == ["Hello", " world"]

    async def test_stream_empty_choices(self, mock_openai):
        chunks_data = [MagicMock(choices=[])]

        class AsyncIter:
            def __init__(self, items):
                self._items = items

            def __aiter__(self):
                self._i = 0
                return self

            async def __anext__(self):
                if self._i >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._i]
                self._i += 1
                return item

        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=AsyncIter(chunks_data)
        )
        provider = OpenAILLMProvider(api_key="test-key")
        collected = []
        async for chunk in provider.stream(_make_messages()):
            collected.append(chunk)
        assert collected == []

    async def test_stream_passes_stream_true(self, mock_openai):
        class AsyncIter:
            def __init__(self, items):
                self._items = items

            def __aiter__(self):
                self._i = 0
                return self

            async def __anext__(self):
                if self._i >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._i]
                self._i += 1
                return item

        mock_openai.return_value.chat.completions.create = AsyncMock(
            return_value=AsyncIter([])
        )
        provider = OpenAILLMProvider(api_key="test-key")
        async for _ in provider.stream(_make_messages()):
            pass
        call_kwargs = mock_openai.return_value.chat.completions.create.call_args
        assert call_kwargs.kwargs["stream"] is True

    def test_model_name(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key", model="gpt-4o-mini")
        assert provider.model_name == "gpt-4o-mini"

    def test_default_model(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key")
        assert provider.model_name == "gpt-4o-mini"

    async def test_message_formatting(self, mock_openai):
        provider = OpenAILLMProvider(api_key="test-key")
        msgs = [
            LLMMessage(role="system", content="sys"),
            LLMMessage(role="user", content="usr"),
            LLMMessage(role="assistant", content="ast"),
        ]
        await provider.complete(msgs)
        call_kwargs = mock_openai.return_value.chat.completions.create.call_args
        formatted = call_kwargs.kwargs["messages"]
        assert formatted == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "assistant", "content": "ast"},
        ]


# ---------------------------------------------------------------------------
# Gemini Provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGeminiLLMProvider:
    @pytest.fixture
    def mock_genai(self):
        with patch("services.llm.providers.gemini_provider.genai") as mock_mod:
            client = MagicMock()
            mock_mod.Client.return_value = client
            client.aio = MagicMock()
            client.aio.models = MagicMock()

            mock_result = MagicMock()
            mock_result.text = "Gemini response"
            mock_result.usage_metadata = MagicMock(
                prompt_token_count=10,
                candidates_token_count=5,
            )
            client.aio.models.generate_content = AsyncMock(return_value=mock_result)
            yield mock_mod

    async def test_complete_returns_response(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        result = await provider.complete(_make_messages())
        assert isinstance(result, LLMResponse)
        assert result.content == "Gemini response"
        assert result.model == "gemini-2.0-flash"
        assert result.usage["prompt_tokens"] == 10
        assert result.usage["completion_tokens"] == 5

    async def test_complete_no_usage_metadata(self, mock_genai):
        mock_genai.Client.return_value.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(text="x", usage_metadata=None)
        )
        provider = GeminiLLMProvider(api_key="test-key")
        result = await provider.complete(_make_messages())
        assert result.usage == {}

    async def test_complete_null_text(self, mock_genai):
        mock_genai.Client.return_value.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(text=None, usage_metadata=None)
        )
        provider = GeminiLLMProvider(api_key="test-key")
        result = await provider.complete(_make_messages())
        assert result.content == ""

    async def test_stream_yields_text(self, mock_genai):
        chunks_data = [MagicMock(text="chunk1"), MagicMock(text="chunk2")]

        class AsyncIter:
            def __init__(self, items):
                self._items = items

            def __aiter__(self):
                self._i = 0
                return self

            async def __anext__(self):
                if self._i >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._i]
                self._i += 1
                return item

        mock_genai.Client.return_value.aio.models.generate_content = AsyncMock(
            return_value=AsyncIter(chunks_data)
        )
        provider = GeminiLLMProvider(api_key="test-key")
        collected = []
        async for chunk in provider.stream(_make_messages()):
            collected.append(chunk)
        assert collected == ["chunk1", "chunk2"]

    async def test_stream_skips_empty_text(self, mock_genai):
        chunks_data = [MagicMock(text="a"), MagicMock(text=None), MagicMock(text="b")]

        class AsyncIter:
            def __init__(self, items):
                self._items = items

            def __aiter__(self):
                self._i = 0
                return self

            async def __anext__(self):
                if self._i >= len(self._items):
                    raise StopAsyncIteration
                item = self._items[self._i]
                self._i += 1
                return item

        mock_genai.Client.return_value.aio.models.generate_content = AsyncMock(
            return_value=AsyncIter(chunks_data)
        )
        provider = GeminiLLMProvider(api_key="test-key")
        collected = []
        async for chunk in provider.stream(_make_messages()):
            collected.append(chunk)
        assert collected == ["a", "b"]

    def test_model_name(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key", model="gemini-2.0-flash")
        assert provider.model_name == "gemini-2.0-flash"

    def test_default_model(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        assert provider.model_name == "gemini-2.0-flash"

    def test_map_messages_system_role(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        mapped = provider._map_messages([LLMMessage(role="system", content="sys")])
        assert mapped[0]["role"] == "user"
        assert mapped[0]["parts"] == [{"text": "sys"}]

    def test_map_messages_user_role(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        mapped = provider._map_messages([LLMMessage(role="user", content="usr")])
        assert mapped[0]["role"] == "user"

    def test_map_messages_assistant_role(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        mapped = provider._map_messages([LLMMessage(role="assistant", content="ast")])
        assert mapped[0]["role"] == "model"

    def test_map_messages_multiple(self, mock_genai):
        provider = GeminiLLMProvider(api_key="test-key")
        mapped = provider._map_messages(_make_messages())
        assert len(mapped) == 2
        assert mapped[0]["role"] == "user"
        assert mapped[1]["role"] == "user"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestCreateLLMProvider:
    def test_openai_factory(self):
        s = Settings(
            AI_PROVIDER="openai",
            OPENAI_API_KEY="sk-test",
            GEMINI_API_KEY="",
        )
        provider = create_llm_provider(s)
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.model_name == "gpt-4o-mini"

    def test_gemini_factory(self):
        s = Settings(
            AI_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            OPENAI_API_KEY="",
        )
        provider = create_llm_provider(s)
        assert isinstance(provider, GeminiLLMProvider)
        assert provider.model_name == "gemini-2.0-flash"

    def test_openai_factory_custom_model(self):
        s = Settings(
            AI_PROVIDER="openai",
            AI_LLM_MODEL="gpt-4o",
            OPENAI_API_KEY="sk-test",
            GEMINI_API_KEY="",
        )
        provider = create_llm_provider(s)
        assert provider.model_name == "gpt-4o"


# ---------------------------------------------------------------------------
# LLMService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLLMService:
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock(spec=LLMProvider)
        provider.model_name = "test-model"
        provider.complete = AsyncMock(
            return_value=LLMResponse(
                content="Generated text",
                model="test-model",
                usage={"prompt_tokens": 5, "completion_tokens": 10},
            )
        )
        return provider

    async def test_generate(self, mock_provider):
        svc = LLMService(mock_provider)
        result = await svc.generate("sys prompt", "user input")
        assert result == "Generated text"
        mock_provider.complete.assert_awaited_once()
        msgs = mock_provider.complete.call_args.args[0]
        assert len(msgs) == 2
        assert msgs[0].role == "system"
        assert msgs[0].content == "sys prompt"
        assert msgs[1].role == "user"
        assert msgs[1].content == "user input"

    async def test_generate_passes_kwargs(self, mock_provider):
        svc = LLMService(mock_provider)
        await svc.generate("sys", "usr", temperature=0.2, max_tokens=50)
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 50

    async def test_generate_default_params(self, mock_provider):
        svc = LLMService(mock_provider)
        await svc.generate("sys", "usr")
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 2048

    async def test_generate_stream(self, mock_provider):
        async def fake_stream(*a, **kw):
            for chunk in ["chunk1", "chunk2", "chunk3"]:
                yield chunk

        mock_provider.stream = fake_stream
        svc = LLMService(mock_provider)
        collected = []
        async for chunk in svc.generate_stream("sys", "usr"):
            collected.append(chunk)
        assert collected == ["chunk1", "chunk2", "chunk3"]

    async def test_generate_stream_empty(self, mock_provider):
        async def fake_stream(*a, **kw):
            return
            yield

        mock_provider.stream = fake_stream
        svc = LLMService(mock_provider)
        collected = []
        async for chunk in svc.generate_stream("sys", "usr"):
            collected.append(chunk)
        assert collected == []

    async def test_summarize(self, mock_provider):
        svc = LLMService(mock_provider)
        result = await svc.summarize("Long text to summarize")
        assert result == "Generated text"
        msgs = mock_provider.complete.call_args.args[0]
        assert msgs[0].role == "system"
        assert "summarizer" in msgs[0].content.lower()
        assert msgs[1].role == "user"
        assert msgs[1].content == "Long text to summarize"

    async def test_summarize_custom_max_length(self, mock_provider):
        svc = LLMService(mock_provider)
        await svc.summarize("text", max_length=200)
        msgs = mock_provider.complete.call_args.args[0]
        assert "200" in msgs[0].content
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["max_tokens"] == 200

    async def test_summarize_low_temperature(self, mock_provider):
        svc = LLMService(mock_provider)
        await svc.summarize("text")
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["temperature"] == 0.3

    def test_provider_property(self, mock_provider):
        svc = LLMService(mock_provider)
        assert svc.provider is mock_provider

    async def test_generate_extra_kwargs_forwarded(self, mock_provider):
        svc = LLMService(mock_provider)
        await svc.generate("sys", "usr", top_p=0.95)
        call_kwargs = mock_provider.complete.call_args.kwargs
        assert call_kwargs["top_p"] == 0.95


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------


class TestLLMProviderABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_subclass_must_implement_methods(self):
        class Incomplete(LLMProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_complete_subclass_instantiable(self):
        class Complete(LLMProvider):
            async def complete(self, messages, **kw):
                return LLMResponse(content="ok", model="m")

            async def stream(self, messages, **kw):
                yield "ok"

            @property
            def model_name(self):
                return "m"

        instance = Complete()
        assert instance.model_name == "m"


# ---------------------------------------------------------------------------
# Integration: Factory -> Service wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestFactoryServiceIntegration:
    @patch("services.llm.providers.openai_provider.AsyncOpenAI")
    async def test_openai_end_to_end(self, mock_cls):
        client = mock_cls.return_value
        client.chat = MagicMock()
        client.chat.completions = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "E2E response"
        client.chat.completions.create = AsyncMock(
            return_value=MagicMock(choices=[mock_choice], usage=None)
        )

        s = Settings(
            AI_PROVIDER="openai",
            OPENAI_API_KEY="sk-test",
            GEMINI_API_KEY="",
        )
        provider = create_llm_provider(s)
        svc = LLMService(provider)
        result = await svc.generate("system", "user")
        assert result == "E2E response"

    @patch("services.llm.providers.gemini_provider.genai")
    async def test_gemini_end_to_end(self, mock_mod):
        client = MagicMock()
        mock_mod.Client.return_value = client
        client.aio = MagicMock()
        client.aio.models = MagicMock()
        client.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(text="Gemini E2E", usage_metadata=None)
        )

        s = Settings(
            AI_PROVIDER="gemini",
            GEMINI_API_KEY="test-key",
            OPENAI_API_KEY="",
        )
        provider = create_llm_provider(s)
        svc = LLMService(provider)
        result = await svc.generate("system", "user")
        assert result == "Gemini E2E"
