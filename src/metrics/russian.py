# src/metrics/russian.py
import textwrap

from deepeval.metrics.answer_relevancy import template as relevancy_tpl
from deepeval.metrics.faithfulness import template as faithful_tpl

# --- Faithfulness ---


def russian_faithfulness_generate_reason(
    score: float, contradictions: list[str], multimodal: bool = False
) -> str:
    return textwrap.dedent(
        f"""Below is a list of Contradictions. It is a list of strings explaining why
        the 'actual output' does not align with the information presented in the
        'retrieval context'. Contradictions happen in the 'actual output', NOT the
        'retrieval context'.
        Given the faithfulness score, which is a 0-1 score indicating how faithful
        the `actual output` is to the retrieval context (higher the better),
        CONCISELY summarize the contradictions to justify the score.

        Expected JSON format:
        {{
            "reason": "The score is <faithfulness_score> because <your_reason>."
        }}

        **
        IMPORTANT: Please make sure to only return in JSON format, with the 'reason'
        key providing the reason.

        ВАЖНО: ОТВЕТ (reason) ДОЛЖЕН БЫТЬ НА РУССКОМ ЯЗЫКЕ.
        Если противоречий нет, просто напиши что-то позитивное и ободряющее
        (но не переусердствуй).

        Your reason MUST use information in `contradiction` in your reason.
        Be sure in your reason, as if you know what the actual output is from
        the contradictions.
        **

        Faithfulness Score:
        {score}

        Contradictions:
        {contradictions}

        JSON:
        """
    )


# --- Answer Relevancy ---


def russian_answer_relevancy_generate_reason(
    irrelevant_statements: list[str],
    input: str,
    score: float,
    multimodal: bool = False,
) -> str:
    return f"""Given the answer relevancy score, the list of reasons of irrelevant
    statements made in the actual output, and the input, provide a CONCISE reason
    for the score. Explain why it is not higher, but also why it is at its current
    score. The irrelevant statements represent things in the actual output that is
    irrelevant to addressing whatever is asked/talked about in the input.
    If there is nothing irrelevant, just say something positive with an upbeat
    encouraging tone (but don't overdo it otherwise it gets annoying).

    **
    IMPORTANT: Please make sure to only return in JSON format, with the 'reason'
    key providing the reason. Ensure all strings are closed appropriately.
    Repair any invalid JSON before you output it.

    VAZHNO: REVIEW THE REASON IN RUSSIAN LANGUAGE.
    ВАЖНО: ПРИЧИНА (REASON) ДОЛЖНА БЫТЬ НА РУССКОМ ЯЗЫКЕ.

    Example JSON:
    {{
        "reason": "The score is <answer_relevancy_score> because <your_reason>."
    }}
    ===== END OF EXAMPLE ======
    **


    Answer Relevancy Score:
    {score}

    Reasons why the score can't be higher based on irrelevant statements:
    {irrelevant_statements}

    Input:
    {input}

    JSON:
    """


# Apply monkeypatches
# Note: mypy doesn't allow method reassignment, so we use type: ignore[method-assign]
faithful_tpl.FaithfulnessTemplate.generate_reason = staticmethod(
    russian_faithfulness_generate_reason
)
relevancy_tpl.AnswerRelevancyTemplate.generate_reason = staticmethod(
    russian_answer_relevancy_generate_reason
)
