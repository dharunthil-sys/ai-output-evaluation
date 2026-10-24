# AI Output Evaluation

A small toolkit for comparing pairs of AI-generated images, videos and chatbot replies against the prompt that produced them, the way human feedback is collected to train generative models.

For each pair, the rater:

1. scores both outputs from 1 to 5 on **adherence** (does it do what the prompt asked), **quality** and **realism**
2. ticks the problems spotted (distorted anatomy, flicker or unnatural motion, text errors, audio that doesn't match the video, missing prompt elements)
3. picks the better output, even when both have flaws
4. writes a short explanation that points to the evidence (a region of the image, a timestamp, a word)

An analysis script then summarises the ratings and flags ones a reviewer would query, such as a preferred output with lower scores than the one it beat.

## What's in the repo

| Path | What it is |
|---|---|
| `tool/evaluate.html` | Rating interface. Runs in any browser with no install: open the file, load `pairs/pairs.json`, select the media files. Click images to zoom; videos loop for replay. Saves as you go and exports `ratings.csv`. |
| `pairs/pairs.json` | 10 prompts across image, video and text, chosen to test common failure points: hands, written text in images, motion physics, tone and length limits. |
| `RUBRIC.md` | Scoring guide for each dimension, what to inspect, and how to decide when both outputs are flawed. |
| `analysis/analyse.py` | Summarises a ratings file: mean scores for preferred vs rejected outputs, which dimension decided most choices, problem frequency, and quality-control flags. |
| `ratings/ratings.csv` | My ratings. |
| `results/` | Summary and charts produced from my ratings. |

## Quality-control checks

`analyse.py` flags a rating when:

- the preferred output has a **lower** average score than the rejected one (the choice contradicts the scores)
- the explanation is under 80 characters (too thin to be evidence-based)
- the scores are tied (the explanation must name the deciding flaw)
- an output scores 2 or below but no problem was ticked

## Run it

```bash
pip install -r requirements.txt
python analysis/analyse.py ratings/ratings.csv --out results
```

Tests (run automatically on every push):

```bash
pytest
```

The test file `tests/fixtures/sample_ratings.csv` is made-up data used only to check the code; it is not part of the results.
