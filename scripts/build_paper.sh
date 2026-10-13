#!/usr/bin/env bash
set -euo pipefail
ARR_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ARR_ROOT/paper"
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
