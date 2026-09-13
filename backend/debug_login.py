"""
Diagnostický skript - ukáže přesně, co server vrátí po pokusu o přihlášení.
Spustit: python debug_login.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = "http://213.29.8.169:55080/fusion/jidelna-objednavky/login.php"
JIDELNA_LOGIN = os.environ.get("JIDELNA_LOGIN", "")
JIDELNA_HESLO = os.environ.get("JIDELNA_HESLO", "")

print(f"Login z .env: '{JIDELNA_LOGIN}'")
print(f"Heslo z .env: '{'*' * len(JIDELNA_HESLO)}' (délka: {len(JIDELNA_HESLO)})")
print()

s = requests.Session()
payload = {
    "desk": "0",
    "log": "1",
    "login": JIDELNA_LOGIN,
    "pass": JIDELNA_HESLO,
}

resp = s.post(LOGIN_URL, data=payload, timeout=10)
resp.encoding = "iso-8859-2"

print("STATUS CODE:", resp.status_code)
print("FINÁLNÍ URL (po případném přesměrování):", resp.url)
print("COOKIES:", s.cookies.get_dict())
print()
print("PRVNÍCH 1500 ZNAKŮ ODPOVĚDI:")
print("-" * 60)
print(resp.text[:1500])
print("-" * 60)
