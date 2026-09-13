from scraper import login, fetch_menu_html, parse_menu

sess = login()
html = fetch_menu_html("20260914", shift=1, day=1, session=sess)
soup_item, items = parse_menu(html, "20260914", 1, 1)

print("Polévky:", soup_item)
print("Počet jídel:", len(items))
for item in items:
    print(f"{item.number}) {item.name} - {item.price} Kč")
