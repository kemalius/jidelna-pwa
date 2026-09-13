from scraper import login, fetch_menu_html, parse_menu

sess = login()
html = fetch_menu_html(dat=None, shift=1, day=1, session=sess)

print("Délka stránky:", len(html))
print()
print("PRVNÍCH 2000 ZNAKŮ:")
print("-" * 60)
print(html[:2000])
print("-" * 60)
print()
print("Hledám 'dat=' v celé stránce:")
import re
found = re.findall(r"dat=\d{8}", html)
print(found[:10])
