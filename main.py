import requests
from bs4 import BeautifulSoup
import re
from functools import reduce
from datetime import datetime


def convert_price_to_eur(mdl):
    conversion_rate = 19.242
    return round(mdl / conversion_rate, 2)


url = "https://maximum.md/ro/electrocasnice-mari/aspiratoare/aparate-de-spalat-pentru-auto/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers)

products_list = []

if response.status_code == 200:
    # parse html using bs4 parser
    soup = BeautifulSoup(response.text, 'html.parser')

    # extract product div
    products = soup.find_all('div', class_='js-content product__item')

    for product in products:
        # extract name
        name_tag = product.find('div', class_='product__item__title')
        name = name_tag.a.text.strip() if name_tag else None
        if name:
            name = re.sub(r'\s+', ' ', name)  # remove extra whitespaces from name

        # extract price
        price_tag = product.find('div', class_='product__item__price-current')
        price = price_tag.text.strip() if price_tag else None
        if price:
            price = re.sub(r'[^0-9]', '', price)  # remove any non-numeric characters from price
            if price.isdigit():
                price = int(price)  # convert price to integer
            else:
                price = None  # set to None if price is not a valid integer

        # extract link
        link_tag = name_tag.find('a') if name_tag else None
        product_link = f"https://maximum.md{link_tag['href']}" if link_tag else None

        # validate data before appending
        if name and price is not None and product_link:
            products_list.append({
                "name": name,
                "price_mdl": price,
                "link": product_link
            })

else:
    print(f"Failed to retrieve the webpage. Status code: {response.status_code}")

# convert mdl to eur
mapped_products = list(map(lambda p: {
    **p,
    "price_eur": convert_price_to_eur(p["price_mdl"])
}, products_list))

# filter by price
min_price = 1000
max_price = 2000
filtered_products = list(filter(lambda p: min_price <= p["price_mdl"] <= max_price, mapped_products))

# calculate sum using reduce
total_sum_mdl = reduce(lambda acc, p: acc + p["price_mdl"], filtered_products, 0)

utc_timestamp = datetime.utcnow().isoformat()
result = {
    "total_sum_mdl": total_sum_mdl,
    "timestamp_utc": utc_timestamp,
    "filtered_products": filtered_products,
}

print(result)
