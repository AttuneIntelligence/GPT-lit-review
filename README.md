## GPT Enabled Literature Curation
Curated by Attune Intelligence, written by Reed Bender.

---

### What the code does

This code contains a collection of Python functions for querying [Pubmed](https://pypi.org/project/pymed/) and [arXiv](https://info.arxiv.org/help/api/index.html), programmatically finding and downloading openly accessible PDF versions of articles with [Unpaywall](https://unpaywall.org/), and then processing those PDFs with GPT-4 to extract relevant metadata including title, authors, publication date, and DOI from these downloaded PDFs.

---

### Setup

To get started, be sure to install the requirements listed in `requirements.txt` onto your local machine.

```bash
pip install -r requirements.txt
```

From there, a Jupyter Lab environment can be launched to run the code interactively. 

```bash
jupyter lab
```

From there, `dev.ipynb` interactively wraps the provided functions for a demonstration of their functionality.