<div align="center">

**[中文](./README_zh.md) | English**

[![GitHub Stars](https://img.shields.io/github/stars/HisMax/RedInk?style=flat&logo=github)](https://github.com/HisMax/RedInk)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-blue)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Docker Pulls](https://img.shields.io/docker/pulls/histonemax/redink)](https://hub.docker.com/r/histonemax/redink)
[![GitHub Release](https://img.shields.io/github/v/release/HisMax/RedInk?include_prereleases)](https://github.com/HisMax/RedInk/releases)

<img src="images/2_en.png" alt="RedInk - Inspiration at Your Fingertips, Making Creation Effortless" width="600"/>

#### [Official Site → Redink.top](https://redink.top)

<img src="images/showcase-grid-en.png" alt="Various social media covers generated with RedInk" width="700" style="border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);"/>

<sub>*Various social media covers generated with RedInk - AI-powered, consistent style, accurate text*</sub>

</div>

---

## ✨ Showcase

### Type One Sentence, Get Complete Image & Text Posts

<details open>
<summary><b>Step 1: Smart Outline Generation</b></summary>

<br>

![Outline Example](./images/example-2.png)

**Features:**
- ✏️ Edit content for each page
- 🔄 Reorder pages (not recommended)
- ✨ Custom description per page (highly recommended)

</details>

<details open>
<summary><b>🎨 Step 2: Cover Page Generation</b></summary>

<br>

![Cover Example](./images/example-3.png)

**Cover Highlights:**
- 🎯 Matches your personal style
- 📝 Accurate text rendering
- 🌈 Visually consistent and coordinated

</details>

<details open>
<summary><b>📚 Step 3: Batch Content Page Generation</b></summary>

<br>

![Content Page Example](./images/example-4.png)

**Generation Notes:**
- ⚡ Concurrent generation for all pages (up to 15 by default)
- ⚠️ Disable high concurrency in settings if your API doesn't support it
- 🔧 Regenerate individual pages you're not satisfied with

</details>

---

## 🏗️ Tech Stack

<table>
<tr>
<td width="50%" valign="top">

### 🔧 Backend

| Technology | Description |
|------|------|
| **Language** | Python 3.11+ |
| **Framework** | Flask |
| **Package Manager** | uv |
| **Text AI** | Gemini 3 |
| **Image AI** | 🍌 Nano Banana Pro |

</td>
<td width="50%" valign="top">

### 🎨 Frontend

| Technology | Description |
|------|------|
| **Framework** | Vue 3 + TypeScript |
| **Build Tool** | Vite |
| **State Management** | Pinia |
| **Styling** | Modern CSS |

</td>
</tr>
</table>

---

## 📦 Deployment

### Option 1: Docker (Recommended)

**The simplest way — one command to start:**

```bash
docker run -d -p 12398:12398 -v ./history:/app/history -v ./output:/app/output histonemax/redink:latest
```

Visit http://localhost:12398 and configure your API Key in the **Settings** page.

**Using docker-compose (optional):**

Download [docker-compose.yml](https://github.com/HisMax/RedInk/blob/main/docker-compose.yml), then:

```bash
docker-compose up -d
```

**Docker Notes:**
- The container does not include any API Keys — configure them in the web UI
- Use `-v ./history:/app/history` to persist history
- Use `-v ./output:/app/output` to persist generated images
- Optional: mount custom config `-v ./text_providers.yaml:/app/text_providers.yaml`

---

### Option 2: Local Development

**Prerequisites:**
- Python 3.11+
- Node.js 18+
- pnpm
- uv

### 1. Clone the Repository
```bash
git clone https://github.com/HisMax/RedInk.git
cd RedInk
```

### 2. Configure API Services

Copy the config templates:
```bash
cp text_providers.yaml.example text_providers.yaml
cp image_providers.yaml.example image_providers.yaml
```

Edit the config files with your API Key and service settings, or configure them later via the **Settings** page in the web UI.

### 3. Install Backend Dependencies
```bash
uv sync
```

### 4. Install Frontend Dependencies
```bash
cd frontend
pnpm install
```

### 5. Start the Services

#### One-Click Start (Recommended)

Run the start script to automatically install dependencies and launch both frontend and backend:

- **macOS**: `start.sh` or double-click `scripts/start-macos.command`
- **Linux**: `./start.sh`
- **Windows**: Double-click `start.bat`

The browser will automatically open at http://localhost:5173

#### Manual Start

**Start Backend:**
```bash
uv run python -m backend.app
```
Visit: http://localhost:12398

**Start Frontend:**
```bash
cd frontend
pnpm dev
```
Visit: http://localhost:5173

### 6. Content Quality Evaluation

Run the default dry-run evaluation without model calls and write JSONL/Markdown reports:

```bash
make eval-quality
```

Compare against a previous report and fail when the score drop exceeds the threshold:

```bash
make eval-quality EVAL_PREVIOUS=reports/xhs-quality-eval.jsonl EVAL_MAX_SCORE_DROP=3
```

Call the live content and quality services:

```bash
make eval-quality EVAL_LIVE=1
```

Append evaluated content to a local case library for human review and future optimization:

```bash
make eval-quality EVAL_CASE_LIBRARY=reports/xhs-content-cases.jsonl EVAL_RUN_ID=manual_eval_001
```

Mark one case after human review:

```bash
uv run python scripts/review_xhs_content_case.py --library reports/xhs-content-cases.jsonl --record-id manual_eval_001:coffee_beginner --publishable true --viral-potential 5 --issue-type hook_weak --selected-title "收藏：新手如何学会手冲咖啡完整流程" --notes "Ready for publishing"
```

Summarize reviewed cases and export high-quality prompt examples:

```bash
make summarize-cases CASE_LIBRARY=reports/xhs-content-cases.jsonl
```

The same command also exports re-evaluated revision examples that meet the quality lift gate:

```bash
make summarize-cases CASE_LIBRARY=reports/xhs-content-cases.jsonl CASE_MIN_QUALITY_OVERALL=85 CASE_MIN_SCORE_DELTA=3
```

Use verified quality examples to guide the next live generation run:

```bash
make eval-quality EVAL_LIVE=1 EVAL_PROMPT_EXAMPLES=reports/xhs-quality-prompt-examples.jsonl
```

Run the full local quality loop in one command:

```bash
make xhs-quality-loop
```

Each loop run writes a full run report and appends a compact replay index:

```text
reports/xhs-quality-loop/runs/<run>/xhs-quality-loop-run.json
reports/xhs-quality-loop/xhs-quality-loop-index.jsonl
```

Summarize replay history across loop runs:

```bash
make summarize-loop
```

The history report includes prioritized diagnostics for baseline failures, missing run reports, re-evaluation regressions, and quality example output.
It also exports `xhs-quality-improvement-plan.jsonl`, a proposed task list for prompt, revision, and eval configuration changes.

Draft human-reviewed execution artifacts from the proposed plan:

```bash
make draft-improvements
```

This writes prompt patch drafts, eval case drafts, revision prompt drafts, and an execution checklist under `reports/xhs-quality-loop/improvement-drafts`.

Dry-run approved draft application before writing candidates:

```bash
make apply-improvements
```

Append only `status=approved` eval case drafts to `xhs-eval-case-candidates.jsonl`:

```bash
make apply-improvements LOOP_APPLY_APPROVED=1
```

Dry-run promotion of candidates marked `status=approved` into a new eval set version:

```bash
make promote-eval-cases
```

Write the new version file without overwriting the base fixture:

```bash
make promote-eval-cases LOOP_PROMOTE_APPROVED=1
```

Enable live services step by step when your provider config is ready:

```bash
make xhs-quality-loop LOOP_LIVE_CONTENT=1 LOOP_LIVE_REVISION=1 LOOP_LIVE_REEVAL=1
```

Plan second-pass revisions for cases that failed gates or human review:

```bash
make plan-revisions REVISION_LIBRARY=reports/xhs-content-cases.jsonl
```

Call the live revision advisor for those planned requests:

```bash
make plan-revisions REVISION_LIBRARY=reports/xhs-content-cases.jsonl REVISION_LIVE=1
```

Write successful revision results back as derived case records:

```bash
make plan-revisions REVISION_LIBRARY=reports/xhs-content-cases.jsonl REVISION_LIVE=1 REVISION_APPEND_CASES=1
```

Apply a saved revision result file to the case library without another live call:

```bash
make plan-revisions REVISION_LIBRARY=reports/xhs-content-cases.jsonl REVISION_APPLY_RESULTS=reports/xhs-revision-results.jsonl REVISION_APPEND_CASES=1
```

Re-evaluate derived revised cases and compare them with their source scores:

```bash
make re-eval-revisions REEVAL_LIBRARY=reports/xhs-content-cases.jsonl
```

Write re-evaluation scores back to the case library:

```bash
make re-eval-revisions REEVAL_LIBRARY=reports/xhs-content-cases.jsonl REEVAL_UPDATE_LIBRARY=1
```

---

## 🔧 Configuration

### Configuration Methods

The project supports two configuration methods:

1. **Web UI (Recommended)**: Visual configuration via the Settings page after starting the service
2. **YAML Files**: Edit config files directly

### Text Generation Config

Config file: `text_providers.yaml`

```yaml
# Active provider
active_provider: openai

providers:
  # OpenAI or compatible API
  openai:
    type: openai_compatible
    api_key: sk-xxxxxxxxxxxxxxxxxxxx
    base_url: https://api.openai.com/v1
    model: gpt-4o

  # Google Gemini (native API)
  gemini:
    type: google_gemini
    api_key: AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gemini-2.0-flash
```

### Image Generation Config

Config file: `image_providers.yaml`

```yaml
# Active provider
active_provider: gemini

providers:
  # Google Gemini image generation
  gemini:
    type: google_genai
    api_key: AIzaxxxxxxxxxxxxxxxxxxxxxxxxx
    model: gemini-3-pro-image-preview
    high_concurrency: false

  # OpenAI compatible API
  openai_image:
    type: image_api
    api_key: sk-xxxxxxxxxxxxxxxxxxxx
    base_url: https://your-api-endpoint.com
    model: dall-e-3
    high_concurrency: false
```

### High Concurrency Mode

- **Off (default)**: Images generated one by one — suitable for GCP $300 trial accounts or rate-limited APIs
- **On**: Images generated in parallel (up to 15 simultaneously) — faster but requires API support for high concurrency

⚠️ **Not recommended for GCP $300 trial accounts** — may trigger rate limits and cause generation failures.

---

## ⚠️ Notes

1. **API Quota Limits**:
   - Be aware of Gemini and image generation API call quotas
   - GCP trial accounts should keep high concurrency disabled

2. **Generation Time**:
   - Image generation takes time — please be patient (don't leave the page)

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

If this project helps you, please give it a Star ⭐

---

## Changelog

### v1.4.2 (2026-03-15)
- ✨ Added English README as default with language toggle (中文/English)
- ✨ Added AI-generated English banner and showcase grid images
- ✨ Added Claude Opus 4.5 to acknowledgments
- ✨ Added shields.io badges (Stars, License, Docker Pulls, Release)
- ✨ Added GitHub Issue/PR templates for standardized contributions
- ✨ Added CONTRIBUTING.md and SECURITY.md
- 🐛 Fixed `rstrip('/v1')` incorrectly stripping URL characters (e.g. `api.openai.com` → `api.openai.co`) — 5 occurrences across backend
- 🐛 Fixed image API test connection failing for chat-based endpoints (Doubao/Volcengine) by using configured endpoint_type instead of hardcoded `/v1/models`
- 🐛 Fixed bare `except:` clause replaced with `except Exception:` in history service
- 🐛 Fixed SSE stream reader not released on error in frontend API layer (resource leak)
- 🐛 Fixed 5 uncleared `setTimeout` calls in ContentDisplay component (memory leak)
- 🐛 Fixed duplicate image regeneration requests by tracking in-progress indices
- 🐛 Fixed GenerateView redirect timer not cleared on component unmount

### v1.4.1 (2025-12-29)
- ✨ Added one-click start scripts for macOS/Linux/Windows
- ✨ Added copywriting generation: auto-generate titles, body text, and tags
- 🔧 Fixed history saving: immediate save after outline generation, auto-save on edit (300ms debounce)
- 🔧 Optimized navigation: force-save unsaved changes before clicking "Start Generation"
- 🔧 Unified startup script port display to 12398
- 🔧 Cleaned up unused retry decorator code in backend generators
- 🔧 Fixed frontend CSS variable reference issues
- 🔧 Optimized checkHistoryExists API performance with dedicated endpoint
- 🔧 Standardized recordId assignment using setRecordId() method

### v1.4.0 (2025-11-30)
- 🏗️ Backend refactored: split monolithic routes into modular blueprints (history, images, generation, outline, config)
- 🏗️ Frontend refactored: extracted reusable components (ImageGalleryModal, OutlineModal, ShowcaseBackground, etc.)
- ✨ Optimized homepage design, removed redundant content blocks
- ✨ Background image preloading with fade-in animation for better loading experience
- ✨ History persistence support (Docker deployment)
- 🔧 Fixed history preview and outline viewing
- 🔧 Optimized Modal component visibility control
- 🧪 Added 65 backend unit tests

### v1.3.0 (2025-11-26)
- ✨ Added Docker support for one-click deployment
- ✨ Published official Docker image to Docker Hub: `histonemax/redink`
- 🔧 Flask auto-detects frontend build artifacts for single-container deployment
- 🔧 Docker image includes blank config templates to protect API Key security
- 📝 Updated README with Docker deployment instructions

### v1.2.0 (2025-11-26)
- ✨ Added copyright info display on all pages
- ✨ Improved image regeneration with single image redraw support
- ✨ Regenerated images maintain style consistency with full context (cover, outline, user input)
- ✨ Fixed image cache issues — regenerated images refresh immediately
- ✨ Unified text generation client supporting Google Gemini and OpenAI-compatible APIs with auto-switching
- ✨ Added web UI configuration for visual API provider management
- ✨ Added high concurrency mode toggle for different API quotas
- ✨ API Key masking for security
- ✨ Auto-save configuration with instant effect
- 🔧 Adjusted default max_output_tokens to 8000 for broader model compatibility
- 🔧 Optimized frontend routing and page layout for better UX
- 🔧 Simplified config file structure, removed redundant parameters
- 🔧 Optimized history image display with thumbnails to save bandwidth
- 🔧 History regeneration auto-loads cover image from filesystem as reference
- 🐛 Fixed missing `store.updateImage` method causing regeneration failure
- 🐛 Fixed image URL concatenation error during history loading
- 🐛 Fixed raw image parameter handling in download function
- 🐛 Fixed image loading 500 error

---

## Community & Support

- **GitHub Issues**: [https://github.com/HisMax/RedInk/issues](https://github.com/HisMax/RedInk/issues)

### Contact the Author

- **Email**: histonemax@gmail.com
- **WeChat**: Histone2024 (please state your purpose)
- **GitHub**: [@HisMax](https://github.com/HisMax)

### Support the Project

<img src="images/coffee.jpg" alt="Buy me a coffee" width="300"/>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=HisMax/RedInk&type=Date)](https://star-history.com/#HisMax/RedInk&Date)

---

## 📄 License

### Personal Use - CC BY-NC-SA 4.0

This project is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)

**You are free to:**
- ✅ **Personal Use** — for learning, research, and personal projects
- ✅ **Share** — copy and redistribute the material in any medium or format
- ✅ **Adapt** — remix, transform, and build upon the material

**Under the following terms:**
- 📝 **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made
- 🚫 **NonCommercial** — You may not use the material for commercial purposes
- 🔄 **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license

### Commercial License

If you wish to use this project for **commercial purposes** (including but not limited to):
- Providing paid services
- Integrating into commercial products
- Operating as a SaaS service
- Other for-profit uses

**Please contact the author for a commercial license:**
- 📧 Email: histonemax@gmail.com
- 💬 WeChat: Histone2024 (please note "Commercial License Inquiry")

The author will provide flexible commercial licensing options based on your specific use case.

---

### Disclaimer

This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability.

---

## 🙏 Acknowledgments

- [Google Gemini](https://ai.google.dev/) — Powerful text generation capabilities
- [Claude Opus 4.5](https://www.anthropic.com/) — Intelligent code assistance and development support
- Image generation service providers — Stunning image generation
- [Linux.do](https://linux.do/) — Excellent developer community

---

## 👨‍💻 Author

**Mozi (Histone)** - AI Entrepreneur

- 🏠 Location: Hangzhou, China
- 🚀 Status: Startup in progress
- 📧 Email: histonemax@gmail.com
- 💬 WeChat: Histone2024 (personal WeChat — no tech support)
- 🐙 GitHub: [@HisMax](https://github.com/HisMax)

*"Let AI do the creative work for us"*

---

**If this project helped you, share it with others!** ⭐

Questions or suggestions? Feel free to open an Issue!
