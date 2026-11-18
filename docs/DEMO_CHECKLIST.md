# December presentation readiness checklist

This project is a small classroom lab, not a production anonymity service. Use only invented accounts and notes.

## Setup

1. Start the local Flask/MySQL application using the documented Docker or Vagrant instructions.
2. Create `alice` and `bob` using `flask --app torbase create-user` inside the app container.
3. Verify `http://127.0.0.1:8080/healthz` returns `{"status":"ok"}`.
4. Start the Tor profile, read the generated onion hostname, and open it in Tor Browser.

## Five-minute demo

1. Sign in as Alice; create, search, edit, and delete a throwaway note.
2. Sign in as Bob; show that Alice's note cannot be viewed or edited (owner isolation).
3. Show the three MySQL tables and one join from `sql/analysis.sql`.
4. Seed synthetic posts, run `scripts/benchmark_sql.py`, and inspect `results/sql/summary.json` and `plans.json`.
5. Run `scripts/benchmark_http.py` from the same client against local and onion URLs; save raw CSV and summary.

## Evidence to capture for the final slides

- Redacted application screenshots, successful login and access-denied behavior.
- Table relationships, one advanced query, and indexing execution plans.
- Actual query medians and HTTP medians, sample sizes, and failures.
- Explicit limitations: HTTP timing is not isolated Tor latency; the site is not production-hardened.

Do not invent numbers or claim tests passed until they have been run on the target environment. Never commit `.env`, real passwords, onion private keys, or personal data.
