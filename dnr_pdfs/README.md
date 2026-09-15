# DNR source reports — provenance record

Full-report PDFs of the Reuters Institute Digital News Report are the source for
`data_collection/outlet_urls/outlets_dnr_<country>.csv` (e.g. `outlets_dnr_switzerland.csv`).

**The PDFs are not in this repository** (~165 MB). This folder holds only the record needed
to obtain exactly the same eleven files: `urls.txt` and the page index below.

Download them into this folder (`*.pdf` here is gitignored), or anywhere you prefer:

```bash
cd dnr_pdfs
while read -r y u; do curl -sL -o "dnr$y.pdf" "$u"; done < urls.txt
```

URLs verified working 12 September 2026.

## Where Switzerland is in each report

`pdf` = page to type into a PDF viewer. `printed` = the page number shown on the page,
which is what goes in the CSV `source` column. They are not always the same.

| Report | pdf page (charts) | printed page |
|---|---|---|
| 2016 | 61 | 61 |
| 2017 | 97 | 97 |
| 2018 | 107 | 107 |
| 2019 | 113 | 113 |
| 2020 | 84 | 84 |
| 2021 | 107 | 107 |
| 2022 | 107 | 107 |
| 2023 | 103 | 103 |
| 2024 | 109 | 109 |
| 2025 | 113 | 113 |
| 2026 | 120 | **117** |

Each Swiss country page carries four charts: offline and online, for the German-speaking
and French-speaking markets. Italian-speaking Switzerland is not surveyed.

## Note on text extraction

`pdftotext` is unreliable on the 2022+ layout — chart labels separate from their values.
Transcribe from the rendered page, not from extracted text.
