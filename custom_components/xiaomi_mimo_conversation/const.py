"""Constants for Xiaomi MiMo Conversation."""

CONF_API_KEY = "api_key"
CONF_LLM_HASS_API = "llm_hass_api"
CONF_PROMPT = "prompt"

DOMAIN = "xiaomi_mimo_conversation"

CONF_ENDPOINT = "endpoint"
CONF_LLM_MODEL = "llm_model"
CONF_ASR_MODEL = "asr_model"
CONF_TTS_MODEL = "tts_model"
CONF_TTS_VOICE = "tts_voice"
CONF_TTS_STYLE = "tts_style"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_TOP_P = "top_p"

DEFAULT_ENDPOINT = "https://api.xiaomimimo.com/v1"
DEFAULT_LLM_MODEL = "mimo-v2.5-pro"
DEFAULT_ASR_MODEL = "mimo-v2.5-asr"
DEFAULT_TTS_MODEL = "mimo-v2.5-tts"
DEFAULT_TTS_VOICE = "mimo_default"
DEFAULT_NAME = "Xiaomi MiMo"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 1.0
DEFAULT_TOP_P = 0.95

BUILT_IN_VOICES = (
    "mimo_default",
    "冰糖",
    "茉莉",
    "苏打",
    "白桦",
    "Mia",
    "Chloe",
    "Milo",
    "Dean",
)

SUGGESTED_VALUES = {
    CONF_ENDPOINT: DEFAULT_ENDPOINT,
    CONF_LLM_MODEL: DEFAULT_LLM_MODEL,
    CONF_ASR_MODEL: DEFAULT_ASR_MODEL,
    CONF_TTS_MODEL: DEFAULT_TTS_MODEL,
    CONF_TTS_VOICE: DEFAULT_TTS_VOICE,
    CONF_TTS_STYLE: "",
    CONF_PROMPT: "You are MiMo, an AI assistant developed by Xiaomi.",
    CONF_MAX_TOKENS: DEFAULT_MAX_TOKENS,
    CONF_TEMPERATURE: DEFAULT_TEMPERATURE,
    CONF_TOP_P: DEFAULT_TOP_P,
    CONF_LLM_HASS_API: [],
}

CONF_REQUIRED = (CONF_ENDPOINT, CONF_API_KEY)
