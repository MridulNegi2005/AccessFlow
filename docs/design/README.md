# Frontend design handoff — 23 September 2026

The user approved two views of one voice-first AccessFlow interface. This package
turns those approvals into an implementable brief for Atishay and a Stitch prompt pack.
No frontend, perception, controller or shared contract implementation was changed.
Mridul's implementation/evaluation goal remains paused.

## Follow-on implementation update — 24 September 2026

The approved voice-first shell is now implemented in the owned demo UI; see
[`IMPLEMENTATION_REPORT_2026-09-24.md`](IMPLEMENTATION_REPORT_2026-09-24.md) for the exact
change inventory, browser checks and limitations. Prompts 1–5 were subsequently run in the
linked Stitch project, but its approved PNGs were not attached and native exports are still
missing. See [`stitch/README.md`](stitch/README.md) for the exact manual export procedure.
The planning notes below retain their original 23 September context.

## Selected route: Stitch first

| Route | Best use | Recommendation |
|---|---|---|
| Same references + DESIGN.md → Stitch → Atishay's coding agent | Generate consistent states, review the prototype, then implement in the existing demo | Selected by the user |
| Approved PNGs + DESIGN.md → Atishay's coding agent directly | Implement without the Stitch stage | Earlier recommendation; not the selected workflow |

The user's follow-up selects Stitch first. Atishay should follow STITCH_PROMPTS.md
in order, retain accepted exports, and then implement them in the existing demo.
The earlier direct-first recommendation is superseded.
Stitch is useful for visual exploration but does not establish correct microphone,
turn-taking, cancellation, state provenance or controller integration.

Google's March announcement describes image/text/code context, DESIGN.md import/export,
variants and connected interactive prototypes. Its May update describes exports to
development tools. These capabilities were checked against official sources on
23 September 2026; no Stitch account/project was opened or generated in this task.

- [Google: design canvas, DESIGN.md and prototypes](https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/)
- [Google: current design and export workflow](https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-updates/)

## Files to give Atishay

1. [DESIGN.md](../../DESIGN.md): canonical appearance and interaction rules.
2. [FRONTEND_HANDOFF.md](FRONTEND_HANDOFF.md): implementation sequence, inspected baseline,
   ownership, coordination and acceptance checks.
3. [ATISHAY_AGENT_PROMPT.md](ATISHAY_AGENT_PROMPT.md): complete prompt written in Atishay's voice.
4. [STITCH_PROMPTS.md](STITCH_PROMPTS.md): required first stage, state variants and export handoff.
5. [Photo reference](references/approved-photo-conversation.png) and
   [meeting reference](references/approved-meeting-correction.png).

To start, open ATISHAY_AGENT_PROMPT.md, copy the prompt, and give it
to the coding agent from Atishay's own checkout. The agent must inspect the current
branch instead of relying on the historical checkout instructions in old handoffs.
Do not switch or overwrite Mridul's working checkout to perform B-owned development.

In Stitch, upload both references and import/paste DESIGN.md, then use the prompts
in order. Review the first two screens before generating the additional states.
Export accepted work as references for the coding agent; retain the same design rules.
Do not publish/deploy simply to pass the design between teammates.

## Asset provenance

Both PNGs were generated during the design conversation and approved by the user.
They were copied byte-for-byte into this handoff, with new descriptive filenames.
They are synthetic UI reference images, not screenshots of implemented functionality,
live model output, calendar events or real user uploads. Their hashes are recorded
in [reference-manifest.json](references/reference-manifest.json).

The rejected repair-focused mockup is intentionally excluded. The approved references
are the only visual anchors; do not revive the repair request sidebar or correction log.
Font choices and hex tokens are proposed implementation values matching the visual
direction, not extracted or measured source artwork specifications.

## What remains work

Atishay must implement and verify the actual frontend, microphone/timing/playback
behavior in his owned areas. Shared event/provenance gaps require both teammates.
The design package itself is not proof that live voice interruption or rich responses
work. No new backend tests or model evaluations were performed for these documents.
