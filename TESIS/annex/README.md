## Annex — Code used for the thesis

Purpose
-------
This folder contains a snapshot of the `LCI` code used to produce the results in the thesis. It is a cleaned copy intended for inclusion as an annex.

Provenance
----------
- Branch: `annex-clean` (snapshot committed on the thesis repo)

Quickstart
----------
1. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
```

2. Install dependencies (if present):

```powershell
pip install -r requirements.txt  # if you have a requirements file
```

3. Run the main script (from repo root):

```powershell
cd annex/LCI
python main.py --help
```

Included
--------
- `LCI/` — source code and CSV data required to reproduce analyses
- `global_parameters.json` — default parameters used in runs

Notes & repro tips
------------------
- The annex keeps the CSV inputs/outputs required for reproducibility.
- Visualization exports (HTML/images) may be regenerated from preserved CSV/JSON result artifacts using tools in `TESIS/annex/LCI/results_tools/`.
- If a `requirements.txt` is missing, install project dependencies listed in the thesis or ask me to generate one from the environment.

License
-------
No license included in this annex. Tell me if you want an `MIT` license added.

Contact
-------
Author: see repository metadata / thesis front matter.
