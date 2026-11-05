# GitHub project

Repository: https://github.com/rbohling/tor_base

Clone the project:

```bash
git clone https://github.com/rbohling/tor_base.git
cd tor_base
```

Follow README.md for Windows/Vagrant or Docker setup. GitHub Actions runs the application tests against MySQL 8.4 on pushes and pull requests.

Never commit .env, database dumps, Tor keys or personal data. The .gitignore excludes local secrets, backups and generated experiment outputs. Add sanitized experimental results explicitly when ready to submit.
