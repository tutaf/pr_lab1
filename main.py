import socket
import ssl
from bs4 import BeautifulSoup
import re
from functools import reduce
from datetime import datetime


def convert_price_to_eur(mdl):
    conversion_rate = 19.242
    return round(mdl / conversion_rate, 2)


def parse_link_content(host, port, path):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # wrap the socket for SSL to handle HTTPS
    context = ssl.create_default_context()
    ssl_client_socket = context.wrap_socket(client_socket, server_hostname=host)

    ssl_client_socket.connect((host, port))

    # send HTTPS GET request to server
    http_request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\r\nConnection: close\r\n\r\n"
    ssl_client_socket.send(http_request.encode())

    # receive the response
    response = b""
    while True:
        chunk = ssl_client_socket.recv(4096)  # read in chunks of 4KB
        if not chunk:
            break
        response += chunk

    # close socket
    ssl_client_socket.close()

    # decode response to a string
    response_str = response.decode()

    # find beginning of response body
    body_index = response_str.find('\r\n\r\n')
    if body_index != -1:
        response_text = response_str[body_index + 4:]  # extract the body of the response
    else:
        print("Could not find the body of the response.")
        response_text = ""

    return response_text


products_list = []

productlist_content = parse_link_content(
    "maximum.md",
    443,
    "/ro/electrocasnice-mari/aspiratoare/aparate-de-spalat-pentru-auto/"
)

if productlist_content:
    # parse html using bs4 parser
    soup = BeautifulSoup(productlist_content, 'html.parser')

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

# convert mdl to eur
mapped_products = list(map(lambda p: {
    **p,
    "price_eur": convert_price_to_eur(p["price_mdl"])
}, products_list))

# filter by price
min_price = 1000
max_price = 1600
filtered_products = list(filter(lambda p: min_price <= p["price_mdl"] <= max_price, mapped_products))

# calculate sum using reduce
total_sum_mdl = reduce(lambda acc, p: acc + p["price_mdl"], filtered_products, 0)

utc_timestamp = datetime.utcnow().isoformat()
result = {
    "total_sum_mdl": total_sum_mdl,
    "timestamp_utc": utc_timestamp,
    "filtered_products": filtered_products,
}


def dict_to_json(dictionary):
    return str(dictionary).replace("'", "\"")


def dict_to_xml(dictionary):
    xml_str = "<result>\n"
    xml_str += f"  <total_sum_mdl>{dictionary['total_sum_mdl']}</total_sum_mdl>\n"
    xml_str += f"  <timestamp_utc>{dictionary['timestamp_utc']}</timestamp_utc>\n"
    xml_str += "  <filtered_products>\n"
    for product in dictionary['filtered_products']:
        xml_str += "    <product>\n"
        xml_str += f"      <name>{product['name']}</name>\n"
        xml_str += f"      <price_mdl>{product['price_mdl']}</price_mdl>\n"
        xml_str += f"      <price_eur>{product['price_eur']}</price_eur>\n"
        xml_str += f"      <link>{product['link']}</link>\n"
        xml_str += "    </product>\n"
    xml_str += "  </filtered_products>\n"
    xml_str += "</result>"
    return xml_str

def custom_serialization(data):
    lines = []

    for key, value in data.items():
        if isinstance(value, list):
            for item in value:
                item_parts = [f"{key}"]
                for sub_key, sub_value in item.items():
                    item_parts.append(f"{sub_key}:{sub_value}")
                lines.append("|".join(item_parts))
        elif isinstance(value, dict):
            item_parts = [f"{key}"]
            for sub_key, sub_value in value.items():
                item_parts.append(f"{sub_key}:{sub_value}")
            lines.append("|".join(item_parts))
        else:
            lines.append(f"{key}|{value}")

    return "\n".join(lines)


def custom_deserialization(serialized_data):
    lines = serialized_data.split('\n')
    data = {}

    for line in lines:
        parts = line.split('|')
        key = parts[0]

        # elements with duplicate keys are treated as elements of the same list
        if key not in data:
            if len(parts) > 2:  # an object with multiple key-value pairs
                data[key] = []
                item = {}
                for part in parts[1:]:
                    sub_key, value = part.split(':', 1)
                    if value.isdigit():
                        item[sub_key] = int(value)
                    else:
                        try:
                            item[sub_key] = float(value)
                        except ValueError:
                            item[sub_key] = value
                data[key].append(item)
            else:  # this is a primitive (a single key-value pair)
                value = parts[1]
                if value.isdigit():
                    data[key] = int(value)
                else:
                    try:
                        data[key] = float(value)
                    except ValueError:
                        data[key] = value
        else:
            # append additional objects to the list if key is repeated
            item = {}
            for part in parts[1:]:
                sub_key, value = part.split(':', 1)
                if sub_key in ["price_mdl", "price_eur"]:
                    value = float(value) if "." in value else int(value)
                item[sub_key] = value
            data[key].append(item)

    return data


print(dict_to_json(result))
print(dict_to_xml(result))
print(custom_serialization(result))


aaa = """total_sum_mdl|1599
timestamp_utc|2024-10-08T17:22:27.542182
filtered_products|name:Aparat de spălat cu presiune mare Karcher K 2 Modular Range|price_mdl:1599|link:https://maximum.md/ro/6752966/|price_eur:83.1"""
print(dict_to_json(custom_deserialization(aaa)))



