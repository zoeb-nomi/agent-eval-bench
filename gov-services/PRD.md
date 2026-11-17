# PRD: gov-services evaluation set

A bilingual (English/Arabic) question set covering UAE government services, for evaluating an AI agent's ability to answer public-sector questions accurately.

## 1. Users and use cases

1. **AI PM (product manager)** shows a prospective employer (ai71) proof of domain-specific evaluation capability: bilingual, public-sector, source-attributed.
2. **Eval owner** runs an LLM judge against these questions to measure correctness, groundedness, and completeness.
3. **Arabic-speaking reviewer** labels the Arabic subset to establish a human-judge agreement baseline in Arabic.

## 2. Metric

Three axes scored 1–5, same as the main bench:
- **Correctness**: Is the answer factually correct per the source page?
- **Groundedness**: Is every claim supported by the cited URL?
- **Completeness**: Does the answer cover all relevant aspects?

Reported per language: average scores, denominator count, and judge-vs-human agreement (exact match percentage) on a labelled subset.

## 3. Trade-offs

- **Source-limited**: Questions come only from public UAE government service pages (u.ae). Coverage is limited to what those pages describe.
- **Factual, not conversational**: Unlike the main bench's multi-turn episodes, these are single-turn Q&A pairs. They test knowledge retrieval, not dialogue management.
- **Static snapshot**: Each question carries the date the source page was read. Government services change; the dataset dates are not updated.
- **Live judge, no human baseline yet**: Answers are judged by a live model (`anthropic/claude-sonnet-5.5`) and cross-checked by a second live model. Agreement with a human is not measured until a person fills `results/human_label_sheet.csv`. The earlier synthetic-judge figure has been removed.
- **Arabic coverage**: The Arabic set mirrors the English set. A native Arabic reader should review the Arabic labels (questions, reference answers, judgements) before any number are treated as authoritative.