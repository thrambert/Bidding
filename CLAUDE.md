# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Objectif

Gérer les enchères pour le jeu de cartes bridge.

## Stack

- Python 3.13, managed with `uv`
- PyQt6 — desktop GUI
- Pydantic — data models and validation

## Commands

```bash
uv sync                  # install / sync dependencies
uv run python -m bidding.main   # run the app
uv run pytest            # run tests
uv run pytest tests/path/to_test.py::test_name  # single test
```

## Architecture

Standard `src/` layout: source lives in `src/bidding/`, entry point is `src/bidding/main.py`.

- GUI layer: PyQt6 widgets/windows
- Domain layer: Pydantic models for bidding data structures
- No database or network layer yet
