from datetime import date
from scraper import login, fetch_menu_html, parse_menu

print("Datum podle tvého počítače (date.today()):", date.today())
print()

sess = login()

# Pevně zadané datum, o kterém víme, že tam menu je
dat = "20260914"
html = fetch_menu_html(dat, shift=1, day=1, session=sess)

print("Délka stažené stránky (znaků):", len(html))
print()

soup_item, items = parse_menu(html, dat, 1, 1)
print("Polévky:", soup_item)
print("Počet nalezených jídel:", len(items))
for item in items:
    print(item)
