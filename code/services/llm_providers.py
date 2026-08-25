"""Static metadata about each curated LLM provider - display name, its real API-key signup page, and
an honest free/trial/paid classification. Split out of llm_config.py by concern (that module is
litellm mechanics; this is our own curated facts, checked by hand against each vendor's site).

tier values: "free" (an ongoing, no-card tier - not just a signup bonus), "trial" (a one-time credit
that runs out), "paid" (no free access found), "local" (runs on your machine, no vendor key at all),
"unclear" (conflicting reports at the time this was checked). All key_url values were verified against
each vendor's own site - never point these at a guessed URL."""

PROVIDER_INFO = {
    "anthropic": {"name": "Anthropic", "key_url": "https://platform.claude.com/settings/keys",
                  "tier": "paid", "note": "No reliable free tier - a $5 signup credit is inconsistently "
                  "granted, and you still need a billing method on file."},
    "cerebras": {"name": "Cerebras", "key_url": "https://cloud.cerebras.ai/", "tier": "unclear",
                 "note": "Free-tier availability is disputed as of Aug 2026 (reports of both a "
                 "1M-token/day free tier and a card-required $5 credit) - check the dashboard yourself."},
    "cloudflare": {"name": "Cloudflare Workers AI",
                   "key_url": "https://dash.cloudflare.com/?to=/:account/ai/workers-ai", "tier": "free",
                   "note": "10,000 free Neurons/day, forever, no card."},
    "cohere": {"name": "Cohere", "key_url": "https://dashboard.cohere.com/api-keys", "tier": "trial",
               "note": "Trial key: 1,000 calls/month, explicitly not for production."},
    "deepinfra": {"name": "DeepInfra", "key_url": "https://deepinfra.com/dash/api_keys", "tier": "trial",
                  "note": "$5 one-time credit, expires in 90 days."},
    "deepseek": {"name": "DeepSeek", "key_url": "https://platform.deepseek.com/api_keys", "tier": "trial",
                 "note": "5M tokens free for the first 30 days, then paid."},
    "fireworks_ai": {"name": "Fireworks AI",
                      "key_url": "https://app.fireworks.ai/settings/users/api-keys", "tier": "trial",
                      "note": "$1 one-time credit only (~1M tokens on a 70B model)."},
    "friendliai": {"name": "FriendliAI", "key_url": "https://friendli.ai/try-friendli/", "tier": "paid",
                   "note": "No free tier found - pay-per-token from the first call."},
    "gemini": {"name": "Gemini", "key_url": "https://aistudio.google.com/app/apikey", "tier": "free",
               "note": "Free forever, no card - Flash/Flash-Lite models only since April 2026, "
               "~5-15 req/min."},
    "groq": {"name": "Groq", "key_url": "https://console.groq.com/keys", "tier": "free",
             "note": "Free forever, no card - 30 req/min, 14,400 req/day."},
    "huggingface": {"name": "Hugging Face", "key_url": "https://huggingface.co/settings/tokens",
                     "tier": "trial", "note": "Free serverless tier, ~1,000 req/day, smaller models only."},
    "hyperbolic": {"name": "Hyperbolic", "key_url": "https://app.hyperbolic.ai/settings/api-keys",
                    "tier": "trial", "note": "$6 one-time credit (requires phone verification)."},
    "minimax": {"name": "MiniMax", "key_url": "https://platform.minimax.io/login", "tier": "paid",
                "note": "No free tier - you must top up your balance before the first call."},
    "mistral": {"name": "Mistral", "key_url": "https://console.mistral.ai/home?workspace_dialog=apiKeys",
                "tier": "free", "note": "Free 'Experiment' tier, ~1B tokens/month, rate-limited but "
                "covers every model incl. Mistral Large."},
    "moonshot": {"name": "Moonshot AI (Kimi)",
                 "key_url": "https://platform.moonshot.ai/console/api-keys", "tier": "trial",
                 "note": "A small welcome credit is mentioned but the amount isn't confirmed."},
    "nebius": {"name": "Nebius AI Studio", "key_url": "https://studio.nebius.ai/settings/api-keys",
               "tier": "trial", "note": "$5-10 one-time trial credit, no card to sign up."},
    "novita": {"name": "Novita AI", "key_url": "https://novita.ai/settings/key-management",
               "tier": "trial", "note": "$0.5 one-time credit."},
    "nvidia_nim": {"name": "NVIDIA NIM", "key_url": "https://build.nvidia.com/settings/api-keys",
                    "tier": "trial", "note": "1,000-5,000 free eval credits, no card - a trial/"
                    "prototyping catalog, not a renewing tier."},
    "ollama": {"name": "Ollama (local)", "key_url": None, "tier": "local",
               "note": "Runs on your own machine - no vendor key, no bill, ever. Needs Ollama "
               "installed and a model pulled locally."},
    "openai": {"name": "OpenAI", "key_url": "https://platform.openai.com/api-keys", "tier": "paid",
               "note": "No reliable free tier - a $5 signup credit is inconsistently granted, and you "
               "still need a billing method on file."},
    "openrouter": {"name": "OpenRouter", "key_url": "https://openrouter.ai/keys", "tier": "free",
                    "note": "Models ending in :free (see openrouter.ai/openrouter/free for the current "
                    "list - it rotates, and litellm's own model list doesn't include them) are free "
                    "forever, no card, ~20 req/min. Type one in below - the Model field is freely "
                    "editable. Other OpenRouter models are pay-per-use."},
    "perplexity": {"name": "Perplexity", "key_url": "https://www.perplexity.ai/settings/api",
                    "tier": "trial", "note": "$25-50 one-time trial credit for new accounts, then "
                    "prepaid credits."},
    "replicate": {"name": "Replicate", "key_url": "https://replicate.com/account/api-tokens",
                   "tier": "trial", "note": "A small one-time trial credit only - no large free grant."},
    "sambanova": {"name": "SambaNova Cloud", "key_url": "https://cloud.sambanova.ai/apis",
                   "tier": "free", "note": "Permanent free tier, $0/month, all models - plus a "
                   "separate $5 credit good for 3 months."},
    "together_ai": {"name": "Together AI", "key_url": "https://api.together.ai/settings/api-keys",
                     "tier": "paid", "note": "No free trial - a $5 minimum purchase is required upfront."},
    "xai": {"name": "xAI (Grok)", "key_url": "https://console.x.ai/team/default/api-keys", "tier": "trial",
            "note": "$25 one-time credit - or up to $175/month if you opt into sharing your API traffic "
            "for training (a real privacy tradeoff, off by default)."},
}

_TIER_LABEL = {"free": "free", "trial": "trial credit", "paid": "paid", "local": "local",
               "unclear": "unclear"}

_UNKNOWN = {"name": None, "key_url": None, "tier": "unknown",
            "note": "Not in our curated list - check this provider's own site for API key instructions."}


def provider_names():
    """Curated provider codes, sorted (e.g. 'anthropic', 'gemini', 'openai', ...) - typing any other
    litellm-known provider still works, it just won't have a name/tier/note here."""
    return sorted(PROVIDER_INFO)


def provider_options():
    """{code: 'Display Name — tier'} for a provider picker, e.g. 'groq': 'Groq — free'."""
    return {p: f"{info['name']} — {_TIER_LABEL[info['tier']]}" for p, info in PROVIDER_INFO.items()}


def key_info(provider):
    """name/key_url/tier/note for one provider code, or a safe placeholder for an unlisted one."""
    return PROVIDER_INFO.get(provider, _UNKNOWN)
