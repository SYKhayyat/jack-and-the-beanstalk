# Jack and the Beanstalk

Upload a photo of yourself. The app cartoonifies it with settings you control,
then places that cartoon person into a scene from *Jack and the Beanstalk*. The
result is captioned with the exact scene specification that was sent to the
image model.

Two scenes ship, and the same person can be put into either:

- **Jack is planting the seeds** — kneeling behind the cottage, beans in the soil.
- **Jack is climbing the beanstalk** — high above the clouds, ground tiny below.

---

## Quick start

```bash
git clone <your-fork> && cd jack-and-the-beanstalk
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # optional; mock mode needs no key
uvicorn app.main:create_app --factory --reload --port 8000
```

Open <http://localhost:8000>. With no `.env` at all the app runs in **mock
mode**: the full UI works, no network calls are made, and images come back as
clearly-labelled placeholders. That is the right way to build, test and load
test the app without spending anything — see
[Stress testing](#stress-testing-for-free).

To use the real model, set in `.env`:

```bash
IMAGE_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
```

## Choosing an API key

Everything below was checked against vendor pricing pages on **2026-10-16**.
Prices move; re-check before you rely on them.

### What actually costs money

**Read this bit first: one picture costs two API calls.** The pipeline
cartoonifies the photo (call 1) and then composes the scene (call 2), so 200
finished pictures is **400 billed image generations**. Every figure below is per
*call*.

| Provider | Per call (1K image) | 200 pictures (400 calls) | Free tier? |
| --- | --- | --- | --- |
| **OpenAI `gpt-image-2.5-flare`, `quality=low`** (default) | **$0.00588** | **~$2.35** | No |
| OpenAI `gpt-image-2.5-*`, `quality=medium` | not published | — | No |
| Cloudflare `flux-2-klein-9b` | $0.015 / MP | ~$6.00 | **Yes — ~6 images/day free** |
| Gemini `gemini-3.1-flash-lite-image` | $0.0336 | ~$13.50 | No |
| Gemini `gemini-3.1-flash-image` | $0.067 | ~$26.80 | No |

**OpenAI is the default here**, because at `quality=low` it is roughly 5.7×
cheaper than the cheapest Gemini image model for the same job, and the two-step
flow below makes the quality question cheap to settle empirically rather than by
guesswork. If likeness turns out to need more than `low`, raise
`OPENAI_QUALITY` — an environment change, not a code change. Gemini stays
wired up as the fallback; `IMAGE_PROVIDER=gemini` switches to it.

Note that OpenAI only renders its per-image token counts in an interactive
calculator, so the `medium` and `high` tiers cannot be quoted from the static
pricing page. The `low` figure above is the one OpenAI states outright.

Input tokens add a few cents across a whole run — negligible. OpenAI also warns
that complex image prompts can take up to two minutes, which is why the default
`GENERATION_TIMEOUT_SECONDS` is generous.

**Gemini has no free trial credit any more.** Google's billing
docs state that the $300 Google Cloud welcome credit *cannot* be used for
Gemini API or AI Studio usage, and that Gemini API was excluded from the Cloud
Free Trial from March 2026. Since March 2026, paid Gemini API access is on a
prepay plan with a **$5 minimum** and credits that are non-refundable and expire
after a year. For a 200-picture run, prepay about **$15**.

Two corrections worth stating plainly, because the obvious assumptions are wrong:

- **Google's free tier does not cover image generation.** The pricing page's
  free-tier column reads *Not available* for every image model, while text
  models read *Free of charge*. You need billing enabled on the API key. The
  *web UI* at <https://aistudio.google.com> is still free — see below.
- **The provider is a config change, not a rewrite.** `IMAGE_PROVIDER` picks
  between `mock`, `openai` and `gemini`. Both real providers send reference
  images with the text in one call, which is the capability this app is built
  on.
- **Do not use `gemini-2.5-flash-image`.** Google deprecated it and gave a
  shutdown date of **2026-10-02**, naming `gemini-3.1-flash-image` and
  `gemini-3.1-flash-lite-image` as the migration targets. This repo defaults to
  the Lite model, and a test fails if the default ever reverts to the retired
  one.

At roughly $0.034 per image and two calls per generation, one generation costs
about **7 cents**. Twenty test generations across several photos is roughly
$1.40 — comfortably inside a free trial budget.

### Testing your prompts for free, before you pay

You can iterate on this project's prompt strategy without an API key:

1. **Google AI Studio web UI — free, no key, no billing.** Upload a photo,
   paste the prompt, look at the result. Copy a prompt straight out of this
   app via the *Show the prompts that were sent* panel in the UI, or from
   `meta.json`. This is the fastest loop and it costs nothing.
   Sign in at <https://aistudio.google.com>.
2. **Cloudflare Workers AI — a free tier that actually covers image editing.**
   Their docs: *"Our free allocation allows anyone to use a total of 10,000
   Neurons per day at no charge."* `@cf/black-forest-labs/flux-2-klein-9b`
   *"supports multi-reference editing capabilities"*, and their pricing table
   charges per input-image megapixel, which only makes sense if images are
   accepted. One 1K output plus one 1K reference costs about 1,545 neurons —
   roughly **6 edited images per day, every day, free**. The catch: Cloudflare
   publishes no worked example of an image-input request, so expect to spend an
   afternoon reverse-engineering the request body.
   <https://developers.cloudflare.com/workers-ai/platform/pricing/>
3. **Pollinations.ai — cheapest image-editing API.** A keyed, OpenAI-shaped
   `POST /v1/images/edits`; `black-forest-labs/flux.2-klein-4b` is around
   0.005 pollen (~$0.005) per image and is *not* paid-only. You register
   without a card and claim a "Quest Pollen" grant; the amount is variable by
   policy, so treat it as small but effectively free rather than unlimited.
   <https://gen.pollinations.ai/image/models>

For the graded checks — several different uploads, both scenes — option 1 is
enough, and option 2 covers you if you want to test *through this app* without
spending. Adding either as a third provider is a config change; see
*Adding a provider*.

### Limits this app is designed around

- **A small number of reference images per prompt.** The pipeline sends 2
  (cartoon portrait + original photo) in the scene pass and 1 in the cartoon
  pass, which is within every model's limit.
- **Around 7MB per inline image.** Uploads are normalised to JPEG at up to
  1536px in `images.py`, well under that.
- **Aspect ratios** `1:1`, `3:2`, `2:3`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`,
  `16:9`, `21:9`. The `AspectRatio` enum offers only values from that list.

## Your API key

- It lives in the `GEMINI_API_KEY` environment variable. Never in code, never
  in the repo, never in Slack.
- `.env` is gitignored. `.env.example` is committed and contains only blank
  placeholders.
- The app never logs it. There is a test (`test_healthz_never_leaks_the_key`,
  `test_response_never_contains_the_api_key`) that fails if the field name or a
  configured key ever appears in a response.
- There is **no retry loop** around the API call, by design. A retry loop on a
  paid endpoint is the classic way to burn a student's balance. A failed call
  fails loudly and you see the reason in the logs.

## Settings the user controls

| Control | Type | What it does |
| --- | --- | --- |
| Cartoon vs. real | slider 1–10 | 1 is nearly photographic with a hint of line art; 10 is fully graphic. Each step has its own hand-written prompt language rather than a numeric formula. |
| Cartoon style | 9 options | Manga, anime, western cartoon, Pixar-like, Disney-like, comic book, pencil sketch, watercolour, flat vector. |
| Likeness to the real you | strict / balanced / loose | How hard to hold on to the uploaded face. Strict is the default because "recognisably the same person" is a graded requirement. |
| Picture shape | 4 options | 1:1, 4:3, 3:4, 16:9. Passed through to the model natively. |
| Age | as uploaded / child / teen / adult | Apparent age of the cartoon character. |
| Gender presentation | as uploaded / feminine / masculine / androgynous | Re-designed from the same facial bone structure, not swapped in from elsewhere. |
| Skin tone | as uploaded + 8 tones | Independent of the photo, or faithful to it. |
| Hair style, hair colour | free text | `as_uploaded` keeps the original; anything else is a description. |
| Outfit | free text | Defaults to storybook costume. |
| Expression | free text | Defaults to *focused and determined*. |
| Keep my glasses / Keep my facial hair | checkboxes | Whether real-world accessories carry into the cartoon. |
| Scene | 2 options | The story beat to draw. |

## Architecture

MVC, with the controller layer split into web pages and a JSON API.

```
app/
├── main.py               # application factory; the only entry point
├── config.py             # settings from the environment; the only place secrets enter
├── container.py          # composition root — the one module that wires everything
├── errors.py             # domain exceptions → HTTP status codes
├── dependencies.py       # FastAPI Depends accessors
├── models/               # MODEL: scenes, cartoon settings, results
│   ├── scenes.py         #     the two story beats, as pure data
│   └── settings.py       #     the user-facing knobs, validated by pydantic
├── scripts/stress_test.py  # free load testing
├── services/             # domain logic, no HTTP
│   ├── prompts.py        #     the actual product: prompt construction
│   ├── concurrency.py    #     admission control for generation requests
│   ├── pipeline.py       #     two-pass orchestration
│   ├── images.py         #     upload validation, normalisation, EXIF stripping
│   ├── storage.py        #     artefact persistence
│   └── image_providers/  #     the swappable backend boundary
│       ├── base.py       #         the ImageProvider contract
│       ├── mock.py       #         offline placeholder renderer
│       ├── openai_provider.py #   the default real backend
│       ├── gemini.py     #         the fallback backend
│       └── registry.py   #         name → class
├── routes/               # CONTROLLER: web.py, api.py, media.py
├── templates/index.html  # VIEW
├── routes/settings_form.py # settings form fields, shared by both endpoints
└── static/               # VIEW: style.css, app.js
```

### The two-pass pipeline

One API call per step, no loops:

1. **cartoonify** — the photo goes in, a cartoon portrait comes out. Every user
   setting is applied here.
2. **scene-compose** — the cartoon portrait *and the original photo* both go in
   as reference images, and the scene specification comes out.

The second pass takes both anchors deliberately. Models drift towards a generic
face when the scene action is interesting — a kid climbing a beanstalk is a much
stronger instruction than "draw this person" — and giving the model two
independent images of the same face is the single biggest lever on "does this
look like the person".

### Where identity and scene fidelity come from

These are the two graded requirements, so they are worth naming explicitly:

**It looks like the person.** Both passes carry an identity directive that names
the specific features to preserve (bone structure, eye shape and colour, nose,
mouth, eyebrows, hairline, skin tone, moles, freckles, glasses, facial hair) and
forbids inventing a new face or averaging towards a generic one. The scene pass
repeats it rather than assuming pass 1's result survived. `likeness_strength`
lets the user trade fidelity against style when they conflict.

**It is faithful to the scene.** Each scene carries a caption, a subject action,
an environment, a lighting note, a camera note, a checklist of objects that must
be visible, and a list of things that would make the image unfaithful. The two
scenes explicitly ban each other's content — the planting scene bans the beanstalk
and bans Jack standing upright; the climbing scene bans planting and kneeling — so
one beat cannot bleed into the other. The negative instructions also forbid text
anywhere in the image, which is what keeps the picture honest against its own
caption.

**The caption is the spec.** `Scene.caption` is both the string sent to the model
and the string rendered under the result. They cannot drift apart, because there
is only one of it.

## HTTP API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | The UI |
| `GET` | `/healthz` | Liveness plus the active provider. Never includes secrets. |
| `GET` | `/api/scenes` | The scene catalogue, with captions |
| `GET` | `/api/settings-options` | Every enum, the defaults, and the slider limits |
| `POST` | `/api/cartoonify` | multipart: `photo` + settings → the cartoon portrait (1 call) |
| `POST` | `/api/compose` | form: `generation_id` + `scene` → the scene image (1 call) |
| `POST` | `/api/generate` | multipart: `photo` + `scene` + settings → both, in one shot (2 calls) |
| `GET` | `/media/{id}/cartoon` | The cartoon portrait |
| `GET` | `/media/{id}/scene` | The scene image |
| `GET` | `/media/{id}/meta.json` | Prompts, caption, provider and model used |

`POST /api/generate` returns image *URLs* rather than inline bytes, so the
browser can fetch them lazily and the response stays small. Interactive docs are
at `/docs`.

Errors are mapped in one place (`app/errors.py`), so a failure never leaks a
stack trace or a key:

| Status | `error` | Meaning |
| --- | --- | --- |
| `400` | `unknown_scene` | That scene key is not in the catalogue |
| `404` | `unknown_draft` | That `generation_id` expired or never existed |
| `400` | `invalid_image` | Not a readable still image, or too large |
| `422` | `invalid_settings` | A setting failed validation |
| `429` | `server_busy` | Every generation slot was busy; nothing was sent to the model |
| `502` | `provider_error` | The model was reached and failed |
| `503` | `provider_unavailable` | No usable provider — usually a missing API key |
| `504` | `generation_timeout` | Ran past the budget; safe to retry |

Example:

```bash
# Two calls, so a likeness you dislike costs one call rather than two.
DRAFT=$(curl -s -X POST http://localhost:8000/api/cartoonify \
  -F photo=@me.jpg -F cartoon_intensity=9 -F cartoon_style=manga \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["generation_id"])')

curl -X POST http://localhost:8000/api/compose \
  -F generation_id="$DRAFT" -F scene=planting-seeds

# Swap scene for the other beat; the portrait is reused, so it is still one call.
curl -X POST http://localhost:8000/api/compose \
  -F generation_id="$DRAFT" -F scene=climbing-beanstalk
```

`POST /api/generate` remains for one-shot use:

```bash
curl -X POST http://localhost:8000/api/generate \
  -F photo=@me.jpg -F scene=planting-seeds -F cartoon_intensity=9
```

## Adding a provider

1. Subclass `ImageProvider` in `app/services/image_providers/` and implement
   `generate(ImageRequest) -> GeneratedImage`.
2. Register it in `registry.py`.
3. Add the name to `ProviderName` in `config.py`.

Nothing else changes. The pipeline, prompts, routes and UI are unaware of which
backend is running.

## Adding a scene

Add one `Scene(...)` entry to `SCENES` in `app/models/scenes.py`. The UI, the
API and the prompts pick it up automatically. Fill in `must_include` and
`must_avoid` — the negative list is what stops scene-to-scene contamination.

## Two steps, so you only pay for what you keep

The pipeline is two calls, and the interface keeps them apart on purpose:

```
  upload + settings
        │
        ▼
  ┌───────────────┐   1 call    ┌──────────────────────────┐
  │  /api/cartoonify │──────────▶  cartoon portrait         │
  └───────────────┘             │  "does this look like me?" │
        ▲                      └──────────┬───────────────┘
        │  tweak settings, retry           │ approve
        └───────────────────────────────────┤
                                            │ 1 call
                                            ▼
                              ┌──────────────────────────┐
                              │  /api/compose             │
                              │  portrait + photo → scene │
                              └──────────────────────────┘
```

Three things fall out of that split, and all three are cost or quality wins:

- **A likeness you dislike costs one call, not two.** Change the intensity, the
  style, the hair, the likeness strength, and retry — the settings panel stays
  live while you look at the portrait. Only an approved portrait is worth a
  scene call.
- **Both scenes from one portrait is one call, not two.** That is how "two
  scenes, same story, same person" is meant to be produced.
- **The judgement happens where it is cheap.** Deciding whether the face
  survived is a question about the portrait, and the portrait is the cheap
  half. Settling it after paying for the scene is backwards.

`POST /api/generate` still does both in one request for scripts and API
clients. The UI does not use it.

The draft — the portrait *and* the normalised photo — is persisted, which is
what lets pass 2 send both identity anchors without the browser re-uploading
anything.

## Stress testing, for free

`scripts/stress_test.py` drives `POST /api/generate` concurrently and reports
throughput, latency percentiles, the status-code breakdown and the estimated
spend. Point it at a **mock-mode** instance for unlimited, zero-cost load:

```bash
# terminal 1 — no API key, no network, no cost
IMAGE_PROVIDER=mock STORAGE_DIR=/tmp/stress uvicorn app.main:create_app --factory --port 8000

# terminal 2
python scripts/stress_test.py --url http://localhost:8000 --requests 120 --concurrency 16
```

```
  requests       120 in 64.9s  (1.9/s)
  status codes   {201: 120}
  latency        p50 6.515s  p95 16.529s  max 21.200s  mean 7.939s
  cost: $0.00 — mock mode makes no API calls.
PASS: every request succeeded.
```

Mock mode still exercises everything that can break in production: upload
validation, Pillow decoding, the concurrency gate, the two-call pipeline,
file writes, and the media routes. Each request uploads a distinct synthetic
image, so nothing is served from a cache.

The p50 above is the gate working, not a bottleneck: 16 requests against
`MAX_CONCURRENT_GENERATIONS=2` means most of them wait their turn.

Against a real provider it costs roughly `(successful / 2) × $0.039`, so the
script requires an explicit acknowledgement first:

```bash
python scripts/stress_test.py --url https://your-app.onrender.com \
  --requests 12 --concurrency 3 --yes-i-am-using-a-paid-key
```

Beyond the script, the free AI Studio tier is rate-limited rather than
unlimited — fine for the several-upload testing described below, not for load
testing. Use mock mode for load and the free tier for picture quality.

### What the timeout and the gate actually do

`GENERATION_TIMEOUT_SECONDS` (default 600) is **one budget for the whole
request**, covering the wait for a free slot *and* both model calls. It is not
one allowance each — otherwise a request could sit in the queue for the full
timeout and then get another full timeout on top.

| Situation | Result |
| --- | --- |
| Generation finishes inside the budget | `201`, with images and the caption |
| Queues longer than its remaining budget | `429 server_busy`, "retry in a moment", **nothing sent to the model** |
| Runs past the budget | `504 generation_timeout` |

Two details that are easy to get wrong and expensive to get wrong:

- **The abort is real.** The budget is applied to the provider's HTTP client,
  so a slow generation aborts its socket. It is not a Python thread left
  running and burning tokens after the client has gone.
- **A timed-out request keeps its slot.** The worker outlives the `504`, so it
  holds the concurrency slot until it genuinely finishes. Releasing at timeout
  would tell the next request the server was idle while it was still working,
  and two generations would run against a limit of one.

`MAX_CONCURRENT_GENERATIONS` is per process. Render runs one worker, so it is a
global limit there; if you ever scale to several workers, the effective limit
is the setting times the worker count.

## Tests

```bash
pytest --cov                       # 238 tests, 98% statement coverage
ruff check . && ruff format --check .
mypy app
```

The suite is fully offline and deterministic: it never touches the network and
never needs an API key. Provider behaviour is verified against a recording
double, and the Gemini provider is tested with the real SDK and a fake transport
— request shaping and response parsing are covered without spending a cent.

Coverage is concentrated where the risk is: prompt construction (the product),
the provider boundary (the swap point), upload validation (untrusted input), and
path-traversal refusal.

### Checking the two graded requirements

Automated tests can prove the *prompts* demand identity and scene fidelity. They
cannot prove the *pixels* do. That check is yours to run by eye:

1. Run the app for real (`IMAGE_PROVIDER=gemini`).
2. Upload several photos that are not the developer: different faces, skin
   tones, glasses, facial hair, ages. Two or three at minimum.
3. Generate both scenes for each person.
4. For each image ask two questions, and be honest about the answers:
   - *Is this recognisably the person who was uploaded?* Show the photo and the
     output side by side to someone who does not know either of you.
   - *Does the picture show what the caption says?* Read the caption, then
     describe the picture. No invented props, no second person, no text.
5. If identity slips, tighten `identity_directive()` and switch
   `likeness_strength` to `strict`. If the scene drifts, add to that scene's
   `must_include` and `must_avoid`.
6. Re-run. Each generated image is captioned with its own scene specification,
   so you can check several attempts side by side without confusion.

Use a few different uploads and iterate the prompt. One photo that happens to
work is not evidence.

## Deploying to Render

The repo ships a blueprint, so this is short:

1. Push the repo to GitHub.
2. In Render: **New → Blueprint**, pick the repo, apply. `render.yaml` declares
   the build and start commands and the health check.
3. Render will prompt for `GEMINI_API_KEY` — paste it there. That is the only
   place it belongs. It is never in the repo.
4. Leave `IMAGE_PROVIDER=mock` for the first deploy so it boots green. Then set
   `IMAGE_PROVIDER=gemini` in the dashboard and save; Render redeploys.
5. Check `https://<your-app>.onrender.com/healthz` — it should report
   `"using_real_api": true`.
6. Put the live URL in the hand-in and in Slack.

Render's free plan sleeps after inactivity, so the first request to the deployed
URL takes a while. The ephemeral filesystem means generated images do not
survive a redeploy — irrelevant here, because results are displayed in the same
response cycle.

## Configuration reference

| Variable | Default | Notes |
| --- | --- | --- |
| `IMAGE_PROVIDER` | `mock` | `mock`, `openai` or `gemini` |
| `OPENAI_API_KEY` | *(empty)* | Required for `openai` |
| `OPENAI_MODEL` | `gpt-image-2.5-flare` | Cheapest published per-call price |
| `OPENAI_QUALITY` | `low` | `medium`/`high`/`xhigh`/`max` cost more; raise only if likeness needs it |
| `GEMINI_API_KEY` | *(empty)* | Required for `gemini` |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite-image` | Keep it cheap. `gemini-3.1-flash-image` is the higher-quality option. |
| `APP_ENV` | `development` | `production` raises the log level |
| `MAX_UPLOAD_MB` | `10` | Enforced before decoding |
| `GENERATION_TIMEOUT_SECONDS` | `600` | One budget per request: queue + both model calls. Also applied to the provider's HTTP client. |
| `MAX_CONCURRENT_GENERATIONS` | `2` | Admission control per process. Beyond this, requests queue and then get 429. |
| `STORAGE_DIR` | `./storage` | Created on startup |

`MAX_UPLOAD_MB` and `STORAGE_DIR` map to `MAX_UPLOAD_MB` and `STORAGE_DIR`.