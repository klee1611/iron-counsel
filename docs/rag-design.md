# Iron Counsel RAG Improvement Design

**Status:** Design validated; implementation changes made; tests not run; deployed Firestore index unchanged  
**Date:** 2026-10-28

## Understanding summary

- Iron Counsel is a Telegram chatbot that retrieves Game of Thrones script lines and re-contextualizes them as humorous advice for everyday questions.
- The desired effect is deliberately absurd, but answers should still address what the user asked. The humor is metaphorical, not a literal suggestion of violence.
- The bot should be concise, creative, and relevant. Serious questions should receive practical guidance with restrained humor; light questions can receive more ridiculous analogies.
- Replies should follow the user's language rather than always returning English and Traditional Chinese.
- The intended audience is a small community of up to a few hundred people. A few extra seconds of latency are acceptable.
- The project should target $0 in monthly operating cost. The owner accepts complexity when it materially improves quality, but not disproportionate ongoing cost.

## Current state and findings

- `app/rag.py` currently makes one Groq generation call after embedding the query and retrieving quotes from Firestore.
- Query and ingestion embeddings use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through FastEmbed, locally in the Cloud Run process.
- The checked-in `vectors.json` contains 23,911 quote vectors with 384 dimensions. `app/embeddings.py` also documents 384 dimensions.
- `terraform/firestore.tf` contains a manual index-creation command in a comment that specifies 768 dimensions. This is documentation, not a Terraform-managed index resource. The actual deployed index configuration has not been checked.
- The current prompt mandates a three-part response and a full English and Traditional Chinese copy, and requires quote use and GoT analogies. Those requirements plausibly contribute to verbosity and topic drift.
- The bot currently includes up to 10 prior messages in each prompt. The agreed design reduces this to the most recent four messages.

## Final design

### Retrieval and embeddings

Keep the existing local FastEmbed model for both ingestion and query-time embeddings. It avoids adding an embedding API dependency and keeps query and corpus vectors in the same embedding space.

Use 384-dimensional vectors in Firestore. Before changing an existing index, inspect the deployed index and confirm its state. If needed, create the 384-dimensional vector index and wait until it is ready before deleting an old index. Update the repository's manual `gcloud` instruction to 384 so it matches the checked-in vectors and embedding model.

Keep the existing top-five quote retrieval for the first version. Do not add a model-based reranker, planner, or retrieval loop.

### Answer generation

Keep a single Groq generation call. The prompt should:

1. Answer the user's question directly in the first sentence.
2. Respond in the user's language.
3. Adjust the balance of practical advice and absurd humor to the seriousness of the question.
4. Re-contextualize a retrieved line or idea as a comedic analogy, even if the connection is intentionally surprising, while keeping the answer connected to the question.
5. Aim for three to five sentences, without mandatory headings or a second-language translation.
6. Treat dramatic violence as fictional metaphor, not literal advice.
7. Avoid inventing direct quotations. If no quote is retrieved, answer without one.

Include only the latest four conversation messages to support short follow-ups while limiting stale context and prompt length.

### Failure behavior

- If retrieval returns no quotes or Firestore retrieval fails, answer without a quote where possible.
- If Groq is unavailable, return a concise retry message.
- Do not add a second model call as a fallback.

### Evaluation plan

Before implementation, prepare a small representative set of English and Traditional Chinese prompts: serious and light questions, direct and ambiguous requests, and follow-ups. Compare baseline and revised responses for:

- whether the first sentence addresses the question;
- practical value for serious topics;
- humor and creative re-contextualization for light topics;
- brevity and readability;
- language matching; and
- whether any quoted line is actually among the retrieved lines.

This evaluation is a design recommendation only; no tests or evaluation runs have been performed.

## Non-functional requirements and assumptions

- **Cost:** Target $0 per month and add no paid services or production model calls. Existing free quotas are usage-limited and can change; this design cannot guarantee a zero bill if GCP or Groq limits are exceeded.
- **Scale:** Up to a few hundred users.
- **Performance:** Several additional seconds are acceptable for answer quality. Local query embeddings remain in the existing Cloud Run request path.
- **Privacy:** The existing Firestore history and Groq processing are acceptable. Do not add a new external provider.
- **Reliability:** Assume occasional failures are acceptable if the bot gives a short retry message.
- **Maintenance:** Keep the current Cloud Run, Firestore, FastEmbed, and Groq stack. Complexity is acceptable only when it materially improves answer quality.
- **Availability of payment:** Willingness to pay is unproven; keep the project free unless real users demonstrate demand.

## Alternatives and tradeoffs

### Selected: focused single-call RAG

Correct the index setup, focus the prompt on relevance and concise humor, and keep one generation call. This addresses the observed prompt issues and a possible index configuration issue without adding model calls or infrastructure.

### Considered: prompt-only cleanup

This is the simplest change, but it would leave the 768-versus-384 index instruction discrepancy unresolved and may not address retrieval failures.

### Deferred: agentic RAG

An agent could rewrite a query, judge retrieved lines, and retrieve again. That may help ambiguous or multi-step questions, but the current use case does not yet justify its extra calls, latency, token use, and maintenance. Reconsider only if evaluation shows specific failures the focused single-call flow cannot address.

## Risks and limits

- The corpus contains only GoT script lines, so some connections to general questions will remain intentionally loose.
- A single-pass flow cannot iteratively reformulate ambiguous queries.
- The index discrepancy is a confirmed repository documentation mismatch, but the deployed index may already be correct. Its contribution to current answer quality is unverified.
- GCP and Groq free quotas do not provide a hard spending cap.
- User willingness to pay has not been validated.

## Decision log

| Decision | Alternatives considered | Reason |
|---|---|---|
| Use focused single-call RAG | Prompt-only cleanup; agentic RAG | Covers prompt behavior and index setup while avoiding additional generation calls and services. |
| Keep local FastEmbed and the existing embedding model | Hosted embedding API or a new model | Existing vectors and query model match at 384 dimensions; a model change requires re-embedding the corpus and adds an external dependency. |
| Align Firestore vector index to 384 dimensions | Retain the 768-dimensional instruction | The model and stored vectors are 384-dimensional; Firestore vector search requires matching dimensions. |
| Prioritize direct, concise answers with adaptive humor | Fixed three-part bilingual format | Better fits questions, avoids duplicated output, and follows the user's language. |
| Keep four recent messages as context | Current ten messages; no history | Supports short follow-ups with less stale context and prompt volume. |
| Defer agentic retrieval | Add query rewrite and result-critique loops now | No measured evidence yet that extra calls would improve this single-corpus comedic use case enough to justify their costs. |
| Maintain a $0 monthly target until demand is demonstrated | Invest in paid hosting or inference | Monetization demand is unproven and this is currently a side project. |

## Implementation-time checks

1. Inspect the actual Firestore vector indexes and their readiness before making index changes.
2. Check current GCP and Groq billing/usage so the $0 target is grounded in actual account usage.
3. Confirm the deployed embedding model and stored vector dimensions match the 384-dimensional local configuration.
