# Run Tor Base on a Mac

Use Docker Desktop on either Apple Silicon (M-series) or Intel. The application, MySQL and Tor run in Linux containers managed by Docker Desktop. You do not need Vagrant, VirtualBox, PowerShell or a host Python installation to start the lab.

## First setup

1. Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), choosing your chip type from Apple menu > About This Mac. Your macOS version must meet Docker's current requirements.
2. Open Docker Desktop and complete its setup prompts. Wait for the engine to be running.
3. Download this repository using GitHub's Code > Download ZIP and extract it, or clone it:

```bash
git clone https://github.com/rbohling/tor_base.git
cd tor_base
```

If you already cloned the repository, open Terminal in that folder and run `git pull --ff-only`. If you downloaded a ZIP, open Terminal in the extracted `tor_base-main` folder instead. Keep the project in a local folder, outside cloud-synced storage.

4. Start the project:

```bash
bash scripts/macos.sh start
```

The launcher checks Docker, generates a private `.env` with containerized Python if missing, builds the app and Tor images, initializes MySQL, and checks the local website. Existing `.env` files and database volumes are preserved. The first run needs internet access and may take several minutes.

5. Create accounts:

```bash
bash scripts/macos.sh user alice
bash scripts/macos.sh user bob
```

Enter separate passwords of at least 12 characters when prompted. Password entry is hidden. Open http://127.0.0.1:8080 to sign in.

## Open the onion website

Install [Tor Browser](https://www.torproject.org/download/) on your Mac. Check startup progress:

```bash
docker compose logs -f tor
```

Wait for `Bootstrapped 100%`, then press Control+C. This exits log viewing without stopping the service. Display the address:

```bash
bash scripts/macos.sh address
```

Open the printed address in Tor Browser. Address generation alone does not prove the service is reachable; allow time for descriptor publication. The login page is reachable by anyone who knows the address, while notes require application login. This deployment does not enable Tor client authorization.

## Everyday commands

```bash
bash scripts/macos.sh start       # Start again, including Tor
bash scripts/macos.sh status      # Check services
bash scripts/macos.sh logs        # View logs
bash scripts/macos.sh stop        # Stop without deleting data
```

For a first local-only test, use `bash scripts/macos.sh start --local`. It does not stop Tor if Tor was already running. To stop an existing onion service while keeping the local website, run `docker compose stop tor`.

Keep Docker Desktop running and the Mac awake during the demo. From a separate Terminal window, `caffeinate -i` prevents idle system sleep until Control+C. Keep the lid open; this does not override lid-close sleep.

## Experiments on macOS

The SQL benchmark runs inside the application container, so no host Python is needed:

```bash
docker compose exec app python -m scripts.seed alice --count 20000
docker compose exec app python -m scripts.benchmark_sql --user-id 1
mkdir -p results
docker compose cp app:/app/results/sql ./results/sql
```

Confirm Alice's ID before using `--user-id 1` if other accounts existed first.

The HTTP benchmark must run on the Mac so both requests come from the same client. This optional step requires Python 3.10 or newer. Keep Tor Browser open and connected:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'requests[socks]==2.32.5'
python -m scripts.benchmark_http --username alice --onion http://YOUR_ADDRESS.onion
```

The default Tor Browser proxy is `socks5h://127.0.0.1:9150`. Use `--proxy` if yours differs. See README.md for interpreting the experiment and avoiding claims of pure Tor latency.

## Troubleshooting

- **docker not found:** finish Docker Desktop installation and reopen Terminal. The launcher also checks Docker Desktop's standard CLI locations.
- **Docker not ready:** the launcher waits up to two minutes; complete first-run prompts in the app and retry.
- **Mount denied:** allow access to the project folder in Docker Desktop file sharing. `.env` generation uses a bind mount.
- **Port 8080 busy:** stop the other app using that port before starting. The launcher's health check expects 8080.
- **Old Intel-only images on Apple Silicon:** do not force `platform: linux/amd64`. This project lets Docker select the native image architecture. Rebuild with `docker compose build --pull` if needed.
- **Changed database password:** editing `.env` does not reset a previously initialized MySQL volume's credentials. Preserve the original file.
- **Slow or unavailable onion access:** verify the local website first and inspect `docker compose logs tor`.

Do not run `docker compose down -v` unless you intend to delete the notes database and onion identity. Keep `.env`, backups and Tor keys private. Use fictional lab notes.

## Verification status

The launcher is written for macOS Bash 3.2. Shell syntax and mocked launcher behavior have been tested in Linux, along with application tests. Actual Docker Desktop execution on Intel/Apple Silicon and live Tor access still require validation on a Mac. The original Word guide's VM-specific setup is superseded by this guide for macOS.

Sources: [Docker Mac installation](https://docs.docker.com/desktop/setup/install/mac-install/), [official MySQL image architectures](https://hub.docker.com/_/mysql), [Tor onion service setup](https://community.torproject.org/onion-services/setup/).
