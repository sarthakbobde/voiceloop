# Good Practices for Projects with Claude

Practical habits for building real projects with Claude Code, drawn from how ticket-triage and
VoiceLoop were built. Each rule has a **why** and a **how**. Skim the checklists at the end if
you only have a minute.

---

## 1. Before you start

### Write down the goal and the finish line
Claude works best when "done" is concrete. "Make a voice agent" is vague. "A voice agent whose
time to first audio is under 1.2 s p50, measured on 30 recorded conversations" is a target.

- State the outcome, the constraints (hardware, budget, time) and what is out of scope.
- Give Claude the real constraints up front: a 4 GB GPU changes every model choice.

### Plan before building, and keep the plan in a file
A plan in chat disappears. A plan in `docs/PLAN.md` survives, can be reviewed, and lets a new
session pick up where the last one stopped.

- Split work into steps that each end with something you can check.
- Keep two files: a **roadmap** (checklist of steps) and a **plan** (how each step is built and
  what "done" means).
- Ask Claude to challenge the plan: what are the risks, what is the cheapest way to test the
  riskiest part first?

### Measure before you change
Build the evaluation first. Every later change is then judged on the same numbers.
ticket-triage ran baselines on untrained models before any training; VoiceLoop builds its latency
harness before adding learned components.

---

## 2. Give Claude durable context

### Keep a `CLAUDE.md` at the repo root
Claude reads it at the start of every session. It is the cheapest way to stop repeating yourself.
Put in it only what Claude cannot work out from the code:

- how to run, test and lint (exact commands)
- conventions the code does not make obvious (naming, where paths are defined, error handling)
- hard rules ("never call the paid API without asking", "never commit data/")
- how you want Claude to work with you (explain first, ask before downloads)

Keep it short. A long file gets skimmed. Link to `docs/` for detail.

```markdown
# CLAUDE.md
## Commands
- Install: `uv sync` · Test: `uv run pytest -q` · Lint: `uv run ruff check src tests`
## Conventions
- All paths come from `paths.py`; never build a path elsewhere.
- CLI handlers only parse options and call package functions.
## Rules
- Ask before any paid API call or download; state the size and source.
- Never commit audio, weights, `.env`, or data files.
## How to work with me
- Explain what you are about to do and why, then do it. I am learning.
```

### Use memory for things about you, not the code
Preferences and lessons that apply across sessions belong in Claude's memory, not in the repo:
"no co-author trailers in commits", "ask before Azure calls", "this laptop throttles on battery".
If you correct Claude twice about the same thing, ask it to remember.

### Record decisions as ADRs
One file (`docs/DECISIONS.md`) with a short entry per decision: context, options, choice,
consequences. Never rewrite an old one; supersede it with a new one. This is what lets you (or
Claude, three weeks later) understand why something is the way it is.

---

## 3. How to ask

### Be specific, and say what you want to learn
Compare:

- Weak: "set up the model."
- Strong: "Download the Qwen2.5-1.5B Q4_K_M GGUF into `models/`, verify the checksum, and explain
  each step because I want to learn how llama.cpp works."

Useful things to include: the goal, where files should go, what to leave alone, how you will
judge success, and whether you want it explained.

### Ask for the explanation you want
Claude adjusts to how you ask. Phrases that work: "explain before you do it", "what are the
trade-offs, then recommend one", "show me the commands you ran", "what could go wrong here?"

### One task at a time
Large asks hide mistakes. Prefer a sequence of small steps, each verified, over one big step.
When the work is independent (for example, two unrelated features), use separate sessions or
subagents so each has a clean context.

### Correct early and specifically
If Claude goes the wrong way, say so at once and say what you want instead. Saying only
"that's wrong" makes it guess. "Use the existing `paths.py`, don't add a new constant file" fixes
it in one turn.

---

## 4. Verify, don't trust

Claude is capable and also wrong sometimes. The fix is verification, and it is cheap.

- **Run it.** Ask Claude to run the tests, the linter and the command, and show the output. "It
  should work" is not evidence.
- **Look at the real numbers.** In VoiceLoop, the first GPU benchmark looked like a broken build.
  Reading the GPU clocks showed the laptop was on battery. A hypothesis is not a finding until
  something confirms it, and a wrong guess (we blamed JIT compilation first) should be said out
  loud and dropped.
- **Check Claude's claims against the source.** For library behaviour, ask it to look at the
  installed version's code or docs, not recall from memory. APIs change (transformers 5, trl 1.x
  broke an earlier notebook).
- **Review the diff.** Read `git diff` before committing. Ask Claude to explain anything you do
  not understand.
- **Use a second look.** `/code-review` or a fresh session reviewing the change finds things the
  author missed.
- **Verify downloads.** Check the size and SHA-256 against the publisher's value; list an archive
  before extracting it. Models and binaries are code you are about to run.

---

## 5. Safety and cost

### Decide what needs your approval, and write it down
Good defaults:

| Always ask first | Fine without asking |
|---|---|
| Paid API calls (state the estimated cost) | Reading files, running tests |
| Downloads (state source, size, destination) | Editing files in the repo |
| Installing system software | Running linters and formatters |
| Pushing, publishing, deleting | Creating a local branch |
| Changing system settings | |

### Keep secrets out
- API keys live in `.env`, which is git-ignored, with a `.env.example` that lists the names only.
- Never paste keys into chat or commit them. If one leaks, rotate it.
- Do not let Claude enter credentials for you; log in yourself.

### Keep data and model files out of git
Add `data/`, `models/`, `*.wav`, `*.gguf`, `*.safetensors` to `.gitignore` on day one. Commit
the scripts that produce them and the small reports that summarise them.

### Watch the cost
- Test on a small sample before a full run (the 50-ticket pilot before 3,300 labels).
- Estimate the cost before the call, and log what was spent.
- Cache results so a failed run does not pay twice.

---

## 6. Code and repo hygiene

- **Production structure, plain code.** Package, one CLI, tests and CI, but readable loops and
  simple functions. Clever code is harder to verify.
- **Separate logic from I/O.** Parsing, scoring and state machines take plain values and are
  tested without a GPU, microphone or network. Thin wrappers handle the hardware.
- **One place for paths and config.** `paths.py` and a YAML config avoid scattered strings.
- **Tests with each feature**, not at the end. Ask for a test that would have caught the bug.
- **CI from the first commit.** Lint, format check and tests on every push.
- **Small commits, clear messages.** One idea per commit. Commit only when you ask Claude to.
- **Branches for risky work.** Keep `main` working.
- **Pin versions** of tools you download (a build number, a lockfile). "Latest" changes under you.
- **Use the lockfile** (`uv.lock`) so the environment is reproducible.

---

## 7. Working across sessions

- **End each session with the repo in a known state:** tests pass, the roadmap is ticked, the plan
  notes what was learned. The next session starts from files, not from memory of the chat.
- **Update the docs when reality differs from the plan.** If a step taught you something, write it
  down. In VoiceLoop, "no C++ compiler" changed the plan to use the prebuilt llama.cpp server, and
  the docs were updated the same day.
- **Long conversations drift.** When a chat gets long or changes topic, start a new session and
  point it at `CLAUDE.md` and the plan.
- **Use separate sessions for separate tasks** (a feature, a review, a research question) so
  context stays clean.
- **Keep experiments reproducible:** record the command, the version and the machine state (for
  example, plugged in or on battery) next to every result.

---

## 8. Learning while you build

If the goal is to learn, say so, and:

- Ask Claude to explain each step *before* running it and to name the concept behind it
  (quantization, JIT compilation, checksums).
- Ask "what would I see if this were wrong?" so you can recognise failures yourself.
- Ask for the command list afterwards, and re-run something yourself to check you can.
- Try the next small step on your own first, then compare with Claude's version.
- Keep a short "what I learned" note per step in `docs/steps/`.

---

## 9. When things go wrong

1. **Read the actual error.** Paste the full message, not a summary.
2. **Ask for a hypothesis list**, then test the cheapest one first.
3. **Change one thing at a time**, and keep a record of what you tried.
4. **Do not retry blindly.** After two or three identical failures, change the approach (as with
   the 504 download: one alternate route, then stop).
5. **Know when to stop and ask.** If the fix needs a decision only you can make (settings, money,
   deleting data), Claude should hand it to you.
6. **Write the lesson down** in memory, the plan or an ADR so it is not paid for twice.

---

## 10. Checklists

### Starting a project
- [ ] Goal, constraints and finish line written down
- [ ] `CLAUDE.md` with commands, conventions and rules
- [ ] `docs/PLAN.md`, `docs/STEPS.md`, `docs/DECISIONS.md`
- [ ] `.gitignore` covers secrets, data and model files
- [ ] Tests and CI run from the first commit
- [ ] An evaluation or baseline exists before any optimisation

### Each working session
- [ ] Say what this session is for and what "done" looks like
- [ ] Ask for the explanation level you want
- [ ] Approve anything paid, downloaded, installed or published, explicitly
- [ ] Verify with real output (tests, numbers), not claims
- [ ] Review the diff before committing
- [ ] Update the roadmap and plan; record decisions
- [ ] Leave the repo clean and green

### Before you share or publish
- [ ] No secrets, personal data or large artefacts in git history
- [ ] README shows how to install, run and test, and states results honestly
- [ ] Limits and failures are documented, not hidden
- [ ] Licences of data and models are checked
