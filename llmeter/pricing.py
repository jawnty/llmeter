"""Reference API pricing per 1M tokens (USD).

This is for cost-equivalence display only. John pays subscription rates,
not these. Numbers are approximate published list prices and will drift —
treat any cost figure as a rough \"what this would cost on metered API.\"
"""

# (input_per_mtok, output_per_mtok, cache_read_per_mtok, cache_write_per_mtok)
PRICES = {
    # Anthropic
    "claude-opus-4":           (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-1":         (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-5":         (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-6":         (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-7":         (15.00, 75.00, 1.50, 18.75),
    "claude-sonnet-4":         (3.00,  15.00, 0.30, 3.75),
    "claude-sonnet-4-5":       (3.00,  15.00, 0.30, 3.75),
    "claude-sonnet-4-6":       (3.00,  15.00, 0.30, 3.75),
    "claude-haiku-4-5":        (1.00,  5.00,  0.10, 1.25),
    # OpenAI (GPT-5 family — Codex defaults)
    "gpt-5":                   (1.25,  10.00, 0.125, 1.25),
    "gpt-5-mini":              (0.25,  2.00,  0.025, 0.25),
    "gpt-5-nano":              (0.05,  0.40,  0.005, 0.05),
    "gpt-5-codex":             (1.25,  10.00, 0.125, 1.25),
    "o4-mini":                 (1.10,  4.40,  0.275, 1.10),
    # Default fallback
    "_default":                (3.00,  15.00, 0.30, 3.75),
}


def _normalize(model: str) -> str:
    if not model:
        return "_default"
    m = model.lower()
    # Strip date suffix: claude-opus-4-7-20260115 -> claude-opus-4-7
    parts = m.split("-")
    while parts and parts[-1].isdigit() and len(parts[-1]) >= 6:
        parts.pop()
    base = "-".join(parts)
    if base in PRICES:
        return base
    # Try progressively shorter prefixes
    for i in range(len(parts), 0, -1):
        cand = "-".join(parts[:i])
        if cand in PRICES:
            return cand
    return "_default"


def cost_usd(model, input_tokens, output_tokens, cache_read_tokens, cache_create_tokens):
    key = _normalize(model)
    p_in, p_out, p_cr, p_cw = PRICES[key]
    # input_tokens reported by APIs is usually the *non-cached* portion
    return (
        (input_tokens or 0) * p_in
        + (output_tokens or 0) * p_out
        + (cache_read_tokens or 0) * p_cr
        + (cache_create_tokens or 0) * p_cw
    ) / 1_000_000
