# Indian Firm Tracking — Data Pipeline

Data-processing scripts for an ongoing research project tracking Indian firms, using Registrar of Companies (RoC) master data.

## Data (not in this repo)

**Source:** Company Master Data from [data.gov.in](https://www.data.gov.in/), pulled per state via the OGD API. Each state file shares the same columns, including: `CIN`, `CompanyName`, `Registered_Office_Address`, `CompanyStatus`, `nic_code`, `CompanyIndustrialClassification`, `CompanyRegistrationdate_date`.

To run any script, place the relevant state CSV(s) in the `data/` folder.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Notes

- Credentials (if any script needs them) go in a local `.env` file
- Outputs are regenerable by re-running the scripts, so they are gitignored rather than committed.
- The strike-off / AGM / Balance-Sheet dates are **not** in the bulk RoC data.
