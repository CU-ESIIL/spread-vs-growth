# Prompt Log

This file records substantive user prompts and the repository changes made in response. Keep entries concise, factual, and useful for reconstructing project intent.

## 2026-07-16

### Prompt

> i just started this repo from a template. I now need to rename and reasign everything to be for the new repo. The purpose of this repo is to compare spread rate and growth rate. I want to make figures for a talk and that involves bigger files and longer runs that I can do in a chat alone. Here is the current storyboard for the talk and we're going to try to animate much of this

### Response Summary

- Retargeted the repository from the starter template to `spread-vs-growth`.
- Updated README, MkDocs configuration, homepage, requirements, ignore rules, and changelog.
- Added project directories for source code, scripts, notebooks, data, outputs, and temporary files.
- Added storyboard and workflow documentation based on the ESA 2026 Fire Metabolism PDF.
- Removed stale template workflows and unused starter website assets.
- Verified the MkDocs site builds in strict mode.

### Prompt

> add an agents.md file and a prompt log

### Response Summary

- Retargeted the existing root `AGENTS.md` with project-specific guidance.
- Added this `PROMPT_LOG.md` file.
- Linked the prompt log from the README.

### Prompt

> i added two videos to the data folder. can you write a python script that puts both those videos in the same image side by side and cuts that into a new video? i want one video with the ink diffusion on one side and the slime mold or ameoba growing on the right.

### Response Summary

- Added `scripts/make_side_by_side_video.py` to stitch the ink diffusion video and slime-mold timelapse into one side-by-side MP4.
- Updated requirements with the video writer dependency.
- Documented the script in the scripts README and workflow docs.

### Prompt

> i see the files in the output folder but they won't open

### Response Summary

- Diagnosed the first render as a valid but nonstandard `1920x540` H.264 MP4.
- Updated the script defaults and writer settings to produce a standard `1920x1080` H.264 MP4 with player-friendly settings.

### Prompt

> now make a perimeter polygon around those at different stages of progress so we can measure the perimeter and area growth through time.

### Response Summary

- Added `scripts/measure_perimeter_growth.py` for stage sampling, segmentation, perimeter tracing, and area/perimeter measurement.
- Added `scikit-image` to requirements for contour tracing and morphology.
- Documented the measurement outputs in the scripts README and workflow docs.

### Prompt

> can you add a log area vs perimter graph for each.

### Response Summary

- Updated `scripts/measure_perimeter_growth.py` to write a two-panel log area-vs-perimeter graph for ink diffusion and slime mold.
- Documented the plot output in the scripts README and workflow docs.
