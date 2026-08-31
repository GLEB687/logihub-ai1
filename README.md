# LogiHub AI — MVP

A Streamlit prototype that compares simulated European freight offers.

## Run locally

1. Open this folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate it.

   Windows PowerShell:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

   macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

5. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

6. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

The terminal will show a local URL, normally `http://localhost:8501`.

## Current MVP features

- Four-block cargo intake flow
- Dynamic city lists for ten European countries
- Ten fictional demo carriers
- Compatibility filtering by mode, timing and services
- Dynamic price and transit-time calculations
- Ranking by price, speed and reliability
- Offer cards with transparent price breakdowns

All carrier names, prices and availability are simulated.
