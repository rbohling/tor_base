"""Generate local-only secrets without overwriting an existing configuration."""
import os
from pathlib import Path
import secrets
p = Path(__file__).resolve().parents[1] / '.env'
try:
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print('.env already exists; left unchanged.')
else:
    db = secrets.token_hex(24)
    with os.fdopen(fd, 'w') as f:
        f.write(f'SECRET_KEY={secrets.token_hex(32)}\nMYSQL_PASSWORD={db}\nMYSQL_ROOT_PASSWORD={secrets.token_hex(32)}\nDATABASE_URL=mysql+pymysql://torbase:{db}@db:3306/torbase?charset=utf8mb4\nCOOKIE_SECURE=0\n')
    print('Created .env. Keep it private. HTTP onion/local lab requires COOKIE_SECURE=0.')
