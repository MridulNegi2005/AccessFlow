# AI assistance disclosure record

AccessFlow was developed with substantial AI coding assistance. OpenAI Codex and Claude
Code generated and revised implementation, tests, documentation and design material.
The team selected the problem, scope and interface direction, directed the agents,
reviewed reported outcomes and performed manual microphone checks. Human line-by-line
authorship of generated implementation is not claimed.

| Area | Assistance and review |
|---|---|
| Concept and scope | Brainstorming, feasibility comparisons and workflow planning; the team selected conversational correction and interruption handling. |
| Controller and tools | Generated contracts, asynchronous orchestration, dependency invalidation, cancellation, stale-result rejection and reconciliation; revisions followed reproduced failures and regression tests. |
| Perception and voice | Generated speech adapters, turn handling and LiveKit integration; checked with deterministic fixtures, recorded audio and manually observed microphone sessions. |
| Interface and extension | Generated design references, Google Stitch prompts, browser implementation and simulated destination tools; design and behavior were selected by the team. |
| Evaluation and packaging | Generated harnesses, metrics, dependency locks and evidence utilities; software checks are distinguished from actual inference and judging. |
| Submission material | Assisted slides, disclosure and project documentation; personal declarations and signatures require human review. |

Representative instructions asked agents to implement the selected scope, preserve
interfaces, repair reproduced audit failures, support continuous voice interruptions,
validate tool execution and package reproducible evaluation. Outputs were revised by
agents following test failures, source review and explicit product decisions. Human
line-level code edits are not documented.

Runtime services are pretrained: Groq `whisper-large-v3` transcribes, LiveKit Inference
`openai/gpt-5.6-luna` plans and `deepgram/aura-2` speaks. No foundation model training
or fine-tuning is claimed.

The latest recorded software suite is 1,614 passed and 8 skipped. Four microphone checks
are human observations, not quantified timing evidence. No official aggregate benchmark
score or clinical accessibility benefit is claimed. External actions are mock tools or
local simulated navigation.

The [AI disclosure form](submission/AccessFlow_AI_Disclosure.docx) provides feature-origin
classifications, output summaries, modifications and required human sign-off.
