import requests
from bs4 import BeautifulSoup

url = "https://maximum.md/ro/electrocasnice-mari/aspiratoare/aparate-de-spalat-pentru-auto/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
response = requests.get(url, headers=headers)

if response.status_code == 200:
    # parse html using bs4 parser
    soup = BeautifulSoup(response.text, 'html.parser')

    # extract product div
    products = soup.find_all('div', class_='js-content product__item')

    for product in products:
        # extract name
        name_tag = product.find('div', class_='product__item__title')
        name = name_tag.a.text.strip() if name_tag else None

        # extract price
        price_tag = product.find('div', class_='product__item__price-current')
        price = price_tag.text.strip() if price_tag else None

        # extract link
        link_tag = name_tag.find('a') if name_tag else None
        product_link = f"https://maximum.md{link_tag['href']}" if link_tag else None

        if name and price and product_link:
            print(f"Product Name: {name}, Price: {price}, Link: {product_link}")

else:
    print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
