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
clearly-labelled placeholders. That is the right way to build and test the UI
without spending anything.

To use the real model, set in `.env`:

```bash
IMAGE_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
```

## Choosing an API key

The assignment asks for a cheap or free option. Recommendation, in order:

| Option | Cost | Why |
| --- | --- | --- |
| **Google AI Studio — `gemini-2.5-flash-image`** (default here) | ~**$0.039 per generated image** ($30/1M output image tokens, 1290 tokens per 1K image); input $0.30/1M tokens. Free tier is rate-limited rather than unlimited — check the current limits in AI Studio. | The only cheap option that accepts **reference images together with text in one call**. That single capability is what this app is built on: pass the cartoon self-portrait *and* the original photo into the scene pass, so the face survives being put into a new scene. Get a key at <https://aistudio.google.com/apikey>. |
| Replicate (`black-forest-labs/flux-kontext-pro`) | ~$5 free trial credit | Good, but a second account, a different SDK, and less predictable identity fidelity. |
| OpenAI `gpt-image-1` | No free tier, ~$0.04–0.17 per image | Higher quality, but you pay from the first test render. |

At $0.039 per image and two calls per generation, one generation costs about
**8 cents**. Twenty test generations across several photos is roughly $1.60.

If Google changes pricing or the model, `GEMINI_MODEL` is an environment
variable — a newer model such as `gemini-3.1-flash-image` is a config change,
not a code change. Note that `gemini-2.5-flash-image` is scheduled for
retirement on 2027-03-15, which is fine for this project but worth knowing.

### Limits this app is designed around

- **Maximum 3 reference images per prompt.** The pipeline sends 2 (cartoon
  portrait + original photo) in the scene pass and 1 in the cartoon pass.
- **Maximum 7MB per inline image.** Uploads are normalised to JPEG at up to
  1536px in `images.py`, well under the ceiling.
- **Supported aspect ratios** are `1:1`, `3:2`, `2:3`, `3:4`, `4:3`, `4:5`,
  `5:4`, `9:16`, `16:9`, `21:9`. The `AspectRatio` enum offers only values from
  that list.

The provider boundary below exists so switching is a config change, not a
rewrite. See *Adding a provider*.

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
├── services/             # domain logic, no HTTP
│   ├── prompts.py        #     the actual product: prompt construction
│   ├── pipeline.py       #     two-pass orchestration
│   ├── images.py         #     upload validation, normalisation, EXIF stripping
│   ├── storage.py        #     artefact persistence
│   └── image_providers/  #     the swappable backend boundary
│       ├── base.py       #         the ImageProvider contract
│       ├── mock.py       #         offline placeholder renderer
│       ├── gemini.py     #         the real implementation
│       └── registry.py   #         name → class
├── routes/               # CONTROLLER: web.py, api.py, media.py
├── templates/index.html  # VIEW
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
| `POST` | `/api/generate` | multipart form: `photo` + `scene` + settings → JSON |
| `GET` | `/media/{id}/cartoon` | The cartoon portrait |
| `GET` | `/media/{id}/scene` | The scene image |
| `GET` | `/media/{id}/meta.json` | Prompts, caption, provider and model used |

`POST /api/generate` returns image *URLs* rather than inline bytes, so the
browser can fetch them lazily and the response stays small. Interactive docs are
at `/docs`.

Example:

```bash
curl -X POST http://localhost:8000/api/generate \
  -F photo=@me.jpg \
  -F scene=planting-seeds \
  -F cartoon_intensity=9 \
  -F cartoon_style=manga \
  -F likeness_strength=strict
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

## Tests

```bash
pytest --cov                       # 148 tests, 98% statement coverage
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
| `IMAGE_PROVIDER` | `mock` | `mock` or `gemini` |
| `GEMINI_API_KEY` | *(empty)* | Required for `gemini` |
| `GEMINI_MODEL` | `gemini-2.5-flash-image` | Keep it cheap |
| `APP_ENV` | `development` | `production` raises the log level |
| `MAX_UPLOAD_MB` | `10` | Enforced before decoding |
| `STORAGE_DIR` | `./storage` | Created on startup |

`MAX_UPLOAD_MB` and `STORAGE_DIR` map to `MAX_UPLOAD_MB` and `STORAGE_DIR`.