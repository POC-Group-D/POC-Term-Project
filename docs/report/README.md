# D4 report

`D4-report-GroupD.tex` is the final report in IEEE conference format
(`IEEEtran`). `D4-report-GroupD.pdf` is the compiled version to submit.

Before submitting, fill in every red **[TODO: ...]** (member contributions)
and recompile.

## Recompile

Either upload `D4-report-GroupD.tex` to [Overleaf](https://www.overleaf.com)
and compile there, or, with Docker Desktop running, in Git Bash from this folder:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(cygpath -w "$PWD"):/w" -w /w texlive/texlive:latest-medium sh -c 'tlmgr install ieeetran >/dev/null; pdflatex D4-report-GroupD.tex && pdflatex D4-report-GroupD.tex'
```

The numbers in the report come from `docs/canary-results.md`,
`docs/cost-report.md`, `docs/api.md` and `docs/data-model.md`.
