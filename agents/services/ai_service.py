import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

def ask_gemini(prompt):
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL"),
        contents=prompt
    )
    return response.text


# ---------------------------------------------------------------------------
# Generic specialist AI call — used by every AI Financial Team specialist
# ---------------------------------------------------------------------------

def ask_specialist(
    data_context: str,
    question: str,
    specialist_name: str,
    persona_prompt: str,
    conversation_context: str | None = None,
    style: str = "concise",
    max_output_tokens: int | None = None,
    stream: bool = False,
    companion_mode: bool = False,
):
    """Send a specialist-scoped prompt to Gemini.

    Parameters
    ----------
    data_context : str
        The domain data the specialist should reason over (financial rows,
        vendor list, compliance records, product knowledge, etc.).
    question : str
        The user's question.
    specialist_name : str
        Name shown to the LLM (e.g. "Atlas", "Orion").
    persona_prompt : str
        One-paragraph description of the specialist's role and boundaries.
    conversation_context : str | None
        Formatted Echo turns for follow-up interpretation.
    style : str
        "concise" for chat, "voice" for spoken replies.
    max_output_tokens : int | None
        Override the default token budget if needed.
    """

    memory_block = ""
    if conversation_context:
        memory_block = (
            "\nPrior conversation (use only to interpret follow-ups; "
            "numbers must come from data below):\n"
            f"{conversation_context}\n"
        )

    if style == "voice":
        style_rules = (
            "Response style (VOICE — critical):\n"
            "- At most 2 short sentences.\n"
            "- Plain speech only. No markdown, no bullets, no emoji, no section headers.\n"
            "- One key number + one comparison or action. Nothing else."
        )
    else:
        style_rules = (
            "Response style (CHAT — critical):\n"
            "- At most 4 short sentences OR up to 5 short bullet lines.\n"
            "- No markdown headings, no emoji section labels.\n"
            "- Lead with the direct answer and the main number.\n"
            "- Optionally one comparison and one concrete next step.\n"
            "- Do not dump full month tables or long essays."
        )

    if companion_mode and specialist_name == "Atlas":
        specialist_name = "Ava"
        persona_prompt = "You are Ava, the AI companion and Chief of Staff. You coordinate the AI Financial Workforce with a warm, professional, human-like connective tone while keeping data grounded."
        style_rules += "\n- COMPANION MODE: Use a warm, natural connective tone. No clinical report headings."

    prompt = (
        f"You are {specialist_name}. {persona_prompt}\n\n"
        f"Available data:\n{data_context}\n"
        f"{memory_block}\n"
        f"User question:\n{question}\n\n"
        "Rules:\n"
        "1. Use ONLY the available data for facts and numbers.\n"
        "2. Use prior conversation only to understand follow-ups.\n"
        "3. If the data cannot answer the question, say so in one sentence.\n"
        f"{style_rules}\n"
    )

    tokens = max_output_tokens
    if tokens is None:
        tokens = 120 if style == "voice" else 280

    try:
        if stream:
            response = client.models.generate_content_stream(
                model=os.getenv("GEMINI_MODEL"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=tokens, 
                    temperature=0.2
                ),
            )
            def stream_generator():
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            return stream_generator()
        else:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=tokens, 
                    temperature=0.2
                ),
            )
            return (response.text or "").strip()
    except Exception as exc:
        logger.exception("%s Gemini call failed: %s", specialist_name, exc)
        if stream:
            return iter(["AI analysis is temporarily unavailable."])
        return ""


# ---------------------------------------------------------------------------
# Backward-compatible wrapper — used by Nova
# ---------------------------------------------------------------------------

def analyze_financial_data(
    financial_data,
    question,
    conversation_context=None,
    style="concise",
    specialist_name="Nova",
):
    """Generate a finance answer (Nova backward compat)."""
    return ask_specialist(
        data_context=financial_data,
        question=question,
        specialist_name=specialist_name,
        persona_prompt="A focused financial specialist covering cash flow, liquidity, payments, collections, and treasury.",
        conversation_context=conversation_context,
        style=style,
    ) or "AI analysis is temporarily unavailable."


# ---------------------------------------------------------------------------
# Synthesis prompt — used by Atlas for multi-specialist collaboration
# ---------------------------------------------------------------------------

def ask_synthesis(
    question: str,
    delegate_results: list[dict],
    data_context: str = "",
    conversation_context: str | None = None,
    style: str = "concise",
    stream: bool = False,
    companion_mode: bool = False,
):
    """Synthesize multiple specialist responses into one executive answer.

    Parameters
    ----------
    question : str
        The original user question.
    delegate_results : list[dict]
        Each dict has ``specialist`` and ``analysis`` keys (and optionally
        other data) from a delegate response.
    data_context : str
        Atlas's own data context (financial rows, etc.).
    conversation_context : str | None
        Formatted Echo turns for follow-up interpretation.
    style : str
        "concise" for chat, "voice" for spoken replies.
    """
    specialist_sections = []
    for result in delegate_results:
        name = result.get("specialist", "Specialist")
        analysis = result.get("analysis", "No response")
        specialist_sections.append(f"--- {name} ---\n{analysis}")
    combined = "\n\n".join(specialist_sections)

    memory_block = ""
    if conversation_context:
        memory_block = (
            "\nPrior conversation (use only to interpret follow-ups; "
            "numbers must come from specialist analyses below):\n"
            f"{conversation_context}\n"
        )

    if style == "voice":
        style_rules = (
            "Response style (VOICE — critical):\n"
            "- At most 3 short sentences.\n"
            "- Plain speech only. No markdown, no bullets, no emoji.\n"
            "- Synthesize the key finding from each specialist into one clear answer."
        )
    else:
        style_rules = (
            "Response style (CHAT — critical):\n"
            "- At most 6 short sentences OR up to 6 short bullet lines.\n"
            "- No markdown headings, no emoji section labels.\n"
            "- Synthesize findings into one cohesive executive answer.\n"
            "- Attribute key findings to the specialist that provided them.\n"
            "- End with one actionable recommendation."
        )

    specialist_name = "Atlas"
    persona_prompt = "You are Atlas, the AI Chief of Staff. You coordinate the AI Financial Workforce."

    if companion_mode:
        specialist_name = "Ava"
        persona_prompt = "You are Ava, the AI companion and Chief of Staff. You coordinate the AI Financial Workforce with a warm, professional, human-like connective tone while keeping data grounded."
        style_rules += "\n- COMPANION MODE: Use a warm, natural connective tone. Start with a natural acknowledgement (e.g. 'I checked with the team'). No clinical report headings."

    prompt = (
        f"{persona_prompt}\n\n"
        "You asked other specialists to investigate a question. "
        "Below are their scoped responses. Synthesize them into one "
        "clear, cohesive executive answer. Do NOT fabricate data.\n\n"
        f"User question:\n{question}\n\n"
        f"Specialist analyses:\n{combined}\n"
        f"{memory_block}\n"
        f"{'Available data:\n' + data_context + chr(10) if data_context else ''}"
        f"Rules:\n"
        "1. Use ONLY the specialist analyses and available data for facts.\n"
        "2. Synthesize — do not just repeat each specialist's answer verbatim.\n"
        "3. Attribute key findings naturally.\n"
        f"{style_rules}\n"
    )

    tokens = 150 if style == "voice" else 400

    try:
        if stream:
            response = client.models.generate_content_stream(
                model=os.getenv("GEMINI_MODEL"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=tokens, 
                    temperature=0.2
                ),
            )
            def stream_generator():
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            return stream_generator()
        else:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=tokens, 
                    temperature=0.2
                ),
            )
            return (response.text or "").strip()
    except Exception as exc:
        logger.exception("Atlas synthesis Gemini call failed: %s", exc)
        if stream:
            return iter(["AI analysis is temporarily unavailable."])
        return ""

