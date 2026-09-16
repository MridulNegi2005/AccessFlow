# Voluntary feedback session template

Use this worksheet only for a voluntary, low-risk review of the AccessFlow prototype. The
facilitator may stop at any time. Written anonymized notes are the default; recording,
uploading or redistributing participant audio, video or screenshots requires specific
agreement before capture.

## Session metadata

- Date:
- Facilitator:
- Participant code: (use a short code; do not record a name here)
- Prototype commit/config:
- Backend label shown to participant: mock / local / hosted
- Device and browser:
- Audio or image capture used: yes / no
- Separate recording consent: yes / no / not requested
- Retention/deletion decision:

## Consent script

Read before any capture:

> We are reviewing an early AccessFlow prototype. Participation is voluntary, and you
> may skip any task or stop without explaining why. The prototype may be incomplete and
> can be wrong. We will use anonymized written notes by default. We will not record,
> upload or share your voice, image or screen unless you specifically agree to that
> capture. This session is not a medical assessment, diagnosis or treatment. Is it okay
> to continue with the selected tasks?

If recording or upload is proposed, obtain a separate, explicit agreement and record the
scope here:

- Capture agreed: audio / video / screen / still image / none
- Purpose:
- Where it may be stored:
- Who may access it:
- Deletion date or deletion request:
- Participant can withdraw before deletion: confirmed / not confirmed

Do not proceed with participant capture when consent is unclear. Do not put names,
contact details, medical information or raw recordings in the repository.

## Task script

Use the same order for each participant and record observations rather than coaching the
participant toward a desired result.

1. **Pause and completion** — Say a request, pause naturally, then finish it.
2. **Repetition** — Repeat a phrase once and observe whether the system preserves meaning.
3. **Correction** — Say “Book Tuesday ... actually Wednesday at five.”
4. **Cancellation** — Start a request and explicitly cancel before any proposed action.
5. **Stale result** — Change the request while an earlier result is pending.
6. **Image evidence** — Provide an image only if the participant has agreed to that
   capture; ask the system to state uncertainty when the image is ambiguous.
7. **Accessibility and control** — Ask whether the acknowledgment, pause handling and
   correction flow feel understandable and interruptible.

For each task, capture only the minimum needed:

- Task:
- Backend label:
- Intended user meaning:
- What the prototype displayed:
- Did it wait for the correction or completion:
- Did it propose or execute an action:
- Any duplicate, stale or premature behavior:
- Participant wording or anonymized paraphrase:
- Severity: blocking / confusing / minor / positive observation
- Facilitator note:

## Closeout

Ask:

- What felt most understandable?
- Where did the system respond too early, too late or with the wrong meaning?
- Did the acknowledgment help you keep speaking?
- Did any label make the backend or uncertainty unclear?
- What should be fixed before another session?

Store anonymized notes in the feedback workspace. Keep raw captures outside the repository
unless the explicit agreement covers repository distribution. Do not use this session to
make claims about diagnosis, speech conditions, population behavior, clinical benefit or
training data. Report feedback as qualitative observations tied to the recorded prototype
commit and backend.
