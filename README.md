# Tor Base

A small graduate database project: a private notes website built with Flask and MySQL, optionally accessed through a Tor v3 onion service.

**Start here:** use fictional data. Create two accounts and a few notes, demonstrate CRUD and access isolation, then seed 20,000 notes and measure the composite index. Run the onion comparison last.

## What is included

- Flask website with login, private notes, categories, title-prefix search, edit and delete.
- Three normalized tables, foreign keys, transactions, a composite index, joins, CTEs and window-function examples.
- Docker Compose deployment, optional Tor service, and a Vagrant/VirtualBox path for Windows.
- Automated application tests and a GitHub Actions job against MySQL 8.4.
- Reproducible SQL and HTTP benchmarks with raw CSV, execution plans and JSON summaries.
- `docs/Project_Guide.docx`, `docs/presentation.md` (slides and complete speaker notes), schema and architecture diagrams.

## macOS quick start (Intel and Apple Silicon)

Install and open [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), then run these commands in the project folder:

```bash
bash scripts/macos.sh start
bash scripts/macos.sh user alice
bash scripts/macos.sh address
```

Open http://127.0.0.1:8080 locally, or open the printed onion address in Tor Browser after Tor finishes bootstrapping. The launcher generates configuration using containerized Python; no host Python, Vagrant or VirtualBox is required for startup.

See **[the macOS guide](docs/MACOS.md)** for installation, updates, stop/start commands and Mac benchmark instructions. This is the current Mac setup guide; the Word guide's VM instructions apply to Windows.

## 1. Windows with Vagrant + VirtualBox

Install Vagrant and VirtualBox from their official sites, reboot if prompted, and reopen PowerShell. Extract this project into a directory you control.

```powershell
cd C:\path\to\tor_base
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
vagrant ssh
```

Inside the VM:

```bash
cd /opt/tor-base
docker compose exec app flask --app torbase create-user alice
docker compose exec app flask --app torbase create-user bob
```

Choose separate passwords of at least 12 characters when prompted. Open **http://127.0.0.1:8080** on Windows. The first build downloads Ubuntu, containers and packages and can take several minutes. Allocate about 3 GB of RAM and sufficient disk space for the VM and images.

`vagrant halt` stops the VM. `vagrant up` restarts it. After restarting the VM, run `docker compose up -d` from `/opt/tor-base` if containers are stopped. Provisioning copies the project into `/opt/tor-base`; edits in the Windows folder are not automatically deployed. For code updates, copy changed source files into that directory and rebuild with `docker compose up -d --build`. Do not overwrite `.env`.

## 2. Docker alternative

With Docker Engine + Compose or Docker Desktop running, and Python 3 installed:

```bash
python scripts/configure.py
docker compose up -d --build
docker compose exec app flask --app torbase create-user alice
docker compose exec app flask --app torbase create-user bob
```

Open **http://127.0.0.1:8080**. Do not commit `.env`. Configuration creates random secrets once and preserves them on reruns. The `init` job creates the schema and shared categories without deleting existing data.

## 3. Start the onion service

Run from the project directory (inside the VM for the Vagrant path):

```bash
docker compose --profile onion up -d --build
docker compose logs tor
docker compose exec tor cat /var/lib/tor/torbase/hostname
```

Wait for Tor to finish bootstrapping, then open the printed `.onion` address in Tor Browser. It can take a few minutes to become reachable. MySQL has no published port. Tor forwards onion port 80 only to the Flask application. The onion identity stays in the `tor_data` volume.

Stop onion access with `docker compose stop tor`. `docker compose down` stops containers and preserves volumes. **Do not add `-v` unless you intentionally want to delete notes and the onion identity.**

## 4. Database demonstration

```bash
docker compose exec app python -m scripts.seed alice --count 20000
docker compose exec app python -m scripts.benchmark_sql --user-id 1
mkdir -p results
docker compose cp app:/app/results/sql ./results/sql
```

User ID 1 assumes Alice was the first account created. Confirm IDs using the MySQL terminal below. Seeding is additive and skips existing synthetic titles. The benchmark uses `Lab 019%`, so the default 20,000 rows provides matches.

Open a MySQL terminal and enter the MYSQL_PASSWORD value from your local `.env` at the prompt:

```bash
docker compose exec db mysql -u torbase -p torbase
```

Copy queries from `sql/analysis.sql`. `sql/schema.sql` is a reference export of the application model, not a migration system. Use `init-db` for the initial schema. Existing schemas will not automatically migrate after model changes.

The SQL experiment alternates queries with the composite index available versus explicitly ignored. It leaves the other indexes intact. Inspect `plans.json` to see whether MySQL actually chose the composite index. Timings include SQL client/driver overhead and result fetching. Report measured medians, not an assumed improvement.

## 5. Local versus onion experiment

Run from **one client computer** that can reach both endpoints. On Windows, keep Tor Browser open (default SOCKS port 9150). Install Python dependencies into a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.benchmark_http --username alice --onion http://YOUR_ADDRESS.onion
```

The benchmark prompts for the password. It signs in separately to both endpoints, warms each session, alternates 20 requests per path and saves results locally. Use `--proxy socks5h://127.0.0.1:9050` if your local Tor client uses port 9050 instead. `socks5h` resolves the onion hostname through Tor.

The HTTP measurements include network, server, application and database work. The reported database round trip includes database driver overhead. Subtracting it from HTTP time does **not** isolate pure Tor latency. Do not use this one-client experiment to generalize to all onion sites.

## Tests

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

The default tests use temporary SQLite databases for fast application validation. To exercise MySQL, set `TEST_DATABASE_URL` to a **disposable** MySQL schema, then run the same command. Tests drop and recreate the test schema's tables. Never point this variable at your notes database. GitHub Actions provisions its own MySQL 8.4 service.

## Backup and recovery

From Terminal on macOS, or a Bash shell in the VM or Linux:

```bash
mkdir -p backups
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --no-tablespaces torbase' > backups/torbase.sql
```

Verify the file is non-empty and keep it private. Restore only into a fresh/disposable lab database after checking the destination:

```bash
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot torbase' < backups/torbase.sql
```

The database dump does not back up the Tor identity or `.env`. Keep those separately if needed. The owner of the machine and database administrators can read stored notes. This is an educational lab, not an audited anonymous publishing platform. There is no login throttling, account recovery, encryption at rest, or production migration framework.

## Troubleshooting

- Check `docker compose ps` and `docker compose logs app init db tor` for failed startup.
- If 8080 is busy, change the host port and use the matching URL.
- If Vagrant cannot start, check hardware virtualization and VirtualBox installation before changing Windows hypervisor settings.
- If Docker says permission denied inside the VM, exit and reconnect with `vagrant ssh` so group membership reloads.
- If Tor cannot bootstrap, test the local site first and check whether the network permits Tor.
- If MySQL login fails after editing `.env`, remember the image applies initial passwords only to an empty database volume. Restore the original credentials or explicitly plan a database reset.

## Submission

See `docs/Project_Guide.docx` for the demo script, study design, test evidence, limitations and completion checklist. `docs/presentation.md` contains every slide and speaker note, plus a link to the editable presentation. Fill in benchmark results after running the target deployment. Do not present pending experiments as completed results.

## Sources

- Tor service setup: https://community.torproject.org/onion-services/setup/
- MySQL EXPLAIN: https://dev.mysql.com/doc/refman/8.4/en/explain.html
- Flask security: https://flask.palletsprojects.com/en/stable/web-security/
- SQLAlchemy sessions: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
- Vagrant: https://developer.hashicorp.com/vagrant/install
