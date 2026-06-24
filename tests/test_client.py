"""Self-checks for the MiMo client helpers."""

import base64
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
PKG = "custom_components.xiaomi_mimo_conversation"
pkg = types.ModuleType(PKG)
pkg.__path__ = [str(ROOT / "custom_components/xiaomi_mimo_conversation")]
sys.modules[PKG] = pkg

for name in ("const", "client"):
    spec = importlib.util.spec_from_file_location(
        f"{PKG}.{name}",
        ROOT / f"custom_components/xiaomi_mimo_conversation/{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"{PKG}.{name}"] = module
    spec.loader.exec_module(module)

client = sys.modules[f"{PKG}.client"]


def test_chat_url_accepts_base_or_full_path():
    assert client.chat_url("https://api.xiaomimimo.com/v1") == (
        "https://api.xiaomimimo.com/v1/chat/completions"
    )
    assert client.chat_url("https://api.xiaomimimo.com/v1/chat/completions") == (
        "https://api.xiaomimimo.com/v1/chat/completions"
    )


def test_stream_json_parses_openai_compatible_sse_lines():
    assert client.stream_json("event: ping") is None
    assert client.stream_json("data: [DONE]") is None
    assert client.stream_json('data: {"choices":[{"delta":{"content":"hi"}}]}') == {
        "choices": [{"delta": {"content": "hi"}}]
    }


def test_first_delta_skips_empty_stream_chunks():
    assert client.first_delta({"choices": []}) == {}
    assert client.first_delta({"choices": [{"delta": {"content": "hi"}}]}) == {
        "content": "hi"
    }


def test_delta_content_treats_null_as_empty_text():
    assert client.delta_content({"choices": [{"delta": {"content": None}}]}) == ""
    assert client.delta_content({"choices": [{"delta": {"content": "hi"}}]}) == "hi"


def test_message_helpers_extract_text_and_audio():
    assert client.message_text({"choices": [{"message": {"content": "ok"}}]}) == "ok"
    raw = b"pcm"
    assert (
        client.message_audio(
            {
                "choices": [
                    {"message": {"audio": {"data": base64.b64encode(raw).decode()}}}
                ]
            }
        )
        == raw
    )
