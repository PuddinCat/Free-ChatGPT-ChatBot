import json
import logging
import asyncio
import traceback
import shodan
import requests_html
import random
import time
import os
from collections import defaultdict
SHODAN_API_COUNT_SAVE_PATH = "shodan_api_count.json"

# 定义API密钥

shodan_api_keys = [
    "pHHlgpFt8Ka3Stb5UlTxcaEwciOeF2QM",
    "v4YpsPUJ3wjDxEqywwu6aF5OZKWj8kik",
    "dTNGRiwYNozXIDRf5DWyGNbkdiS5m3JK",
    "kdnzf4fsYWQmGajRDn3hB0RElbUlIaqu",
    "boYedPn8iDWi6GDSO6h2kz72VLt6bZ3S",
    "FQNAMUdkeqXqVOdXsTLYeatFSpZSktdb",
    "OygcaGSSq46Lg5fZiADAuFxl4OBbn7zm",
    "XAbsu1Ruj5uhTNcxGdbGNgrh9WuMS1B6",
    "nkGd8uVE4oryfUVvioprswdKGmA5InzZ",
    "XYdjHDeJM36AjDfU1feBsyMJIj8XxGzD",
    "OefcMxcunkm72Po71vVtX8zUN57vQtAC",
    "PSKINdQe1GyxGgecYz2191H2JoS9qvgD",
    "61TvA2dNwxNxmWziZxKzR5aO9tFD00Nj",
    "xTbXXOSBr0R65OcClImSwzadExoXU4tc",
    "EJV3A4Mka2wPs7P8VBCO6xcpRe27iNJu",
    "mEuInz8UH1ixLGJq4oQhEiJORERVG5xc",
    "lkY0ng0XMo29zEhzyw3ibQfeEBxghwPF",
    "syeCnFndQ8TE4qAGvhm9nZLBZOBgoLKd",
    "7TeyFZ8oyLulHwYUOcSPzZ5w3cLYib61",
]

shodan_api_count = None

semaphore = asyncio.Semaphore(16)

chatbotui_test_data = json.dumps(
    {
        "model": {
            "id": "gpt-3.5-turbo",
            "name": "GPT-3.5",
            "maxLength": 12000,
            "tokenLimit": 4000,
        },
        "messages": [
            {"role": "user", "content": "Just say your name without doing anything."}
        ],
        "key": "",
        "prompt": "You are ChatGPT, a large language model trained by OpenAI. Follow the user's instructions carefully. Respond using markdown.",
    }
)

chatgpt_next_web_test_data = json.dumps(
    {
        "messages": [
            {
                "role": "system",
                "content": "You are ChatGPT, a large language model trained by OpenAI. Follow the user's instructions carefully. Respond using markdown.",
            },
            {"role": "user", "content": "Just say your name without doing anything."},
        ],
        "stream": True,
        "model": "gpt-3.5-turbo",
        "temperature": 0.5,
        "presence_penalty": 0,
    }
)

with open("template.md", "r") as f:
    TEMPLATE = f.read()

if os.path.exists(SHODAN_API_COUNT_SAVE_PATH):
    with open(SHODAN_API_COUNT_SAVE_PATH, "r") as f:
        shodan_api_count = defaultdict(int, json.load(f))
else:
    shodan_api_count = defaultdict(int, {})


async def isvalid_site(url):
    logging.warning(f"Checking site: {url}")
    try:
        asession = requests_html.AsyncHTMLSession()
        r = await asession.get(url, timeout=2)  # type: ignore
        return r.status_code == 200
    except Exception:
        return False


def scan_targets(query):
    keys = sorted(shodan_api_keys, key=lambda x: shodan_api_count[x], reverse=True)
    # 首先随机尝试几个key能不能使用
    keys = random.choices(keys, k = 3) + keys
    for api_key in keys:
        logging.warning(f"Try {api_key}")
        api = shodan.Shodan(api_key)
        try:
            results = api.search(query)
            for result in results["matches"]:
                url_host = "%s:%s" % (result["ip_str"], result["port"])
                yield "http://" + url_host
                yield "https://" + url_host
            shodan_api_count[api_key] += 1
            break
        except shodan.APIError as e:
            # traceback.print_exc()
            logging.warning("Error: %s" % e)
            if "403" in str(e):
                time.sleep(5)

    with open(SHODAN_API_COUNT_SAVE_PATH, "w") as f:
        json.dump(shodan_api_count, f)


# chatbotui


async def isvalid_chatbot_ui(url):
    """检查一个chatbotui网站是否正常

    Args:
        url (str): url

    Returns:
        bool: 是否正常
    """
    async with semaphore:
        try:
            asession = requests_html.AsyncHTMLSession()
            r = await asession.post(f"{url}/api/chat", timeout=5, data=chatbotui_test_data)  # type: ignore
            return "ChatGPT" in r.text
        except Exception:
            return False


async def valid_chatbotui(urls):
    """过滤所有正常的chatbotui url

    Args:
        urls (list): 所有url

    Returns:
        list: 正常的url
    """
    oks = await asyncio.gather(*[isvalid_site(url) for url in urls])
    urls = [url for url, ok in zip(urls, oks) if ok]
    oks = await asyncio.gather(*[isvalid_chatbot_ui(url) for url in urls])
    urls = [url for url, ok in zip(urls, oks) if ok]
    print("chatbotui: ", urls)
    return urls


# ioanmo226
async def isvalid_ioanmo226(url):
    data = {"prompt": "Please Just say your name and do nothing.", "model": "chatgpt"}
    async with semaphore:
        try:
            asession = requests_html.AsyncHTMLSession()
            r = await asession.post(f"{url}/get-prompt-result", timeout=5, json=data)  # type: ignore
            return "ChatGPT" in r.text
        except Exception:
            return False


async def valid_ioanmo226(urls):
    """过滤所有正常的ioanmo226 url

    Args:
        urls (list): 所有url

    Returns:
        list: 正常的url
    """
    oks = await asyncio.gather(*[isvalid_site(url) for url in urls])
    urls = [url for url, ok in zip(urls, oks) if ok]
    oks = await asyncio.gather(*[isvalid_ioanmo226(url) for url in urls])
    urls = [url for url, ok in zip(urls, oks) if ok]
    print("ioanmo226: ", urls)
    return urls


# chatgpt_next_web
async def isvalid_chatgpt_next_web(url):
    async with semaphore:
        try:
            asession = requests_html.AsyncHTMLSession()
            r = await asession.post(f"{url}/api/openai/v1/chat/completions", timeout=5, data=chatgpt_next_web_test_data)  # type: ignore
            lines = [line.removeprefix("data: ") for line in r.text.split("\n") if line.startswith("data: ")]
            data = [
                json.loads(line)["choices"][0]["delta"].get("content", "") for line in lines if line != "[DONE]"
            ]
            text = "".join(data)
            return "ChatGPT" in text
        except Exception:
            return False


async def valid_chatgpt_next_web(urls):
    """过滤所有正常的chatgpt_next_web url

    Args:
        urls (list): 所有url

    Returns:
        list: 正常的url
    """
    oks = await asyncio.gather(*[isvalid_site(url) for url in urls])
    urls = [url for url, ok in zip(urls, oks) if ok]
    oks = await asyncio.gather(*[isvalid_chatgpt_next_web(url) for url in urls])
    urls = [url for url, ok in zip(urls, oks) if ok]
    print("chatgpt_next_web: ", urls)
    return urls


async def valid_detail(detail):
    """检查一个detail是否正常"""
    types = {
        "chatbotui": isvalid_chatbot_ui,
        "ioanmo226": isvalid_ioanmo226,
        "chatgpt_next_web": isvalid_chatgpt_next_web,
    }
    if "type" not in detail or detail["type"] not in types:
        return False
    return await types[detail["type"]](detail["url"])


async def filter_valid_details(details):
    oks = await asyncio.gather(*[valid_detail(detail) for detail in details])
    return [detail for detail, ok in zip(details, oks) if ok]


async def new_sites_details():
    configs = [
        (
            '"ChatGPT but better."',
            valid_chatbotui,
            "chatbotui"
        ),
        (
            '"Experience OpenAI API with this simple web application"',
            valid_ioanmo226,
            "ioanmo226"
        ),
        (
            '"ChatGPT Next Web"',
            valid_chatgpt_next_web,
            "chatgpt_next_web"
        ),
    ]
    new_sites_details = []
    for shodan_prompt, func, detail_type in configs:
        shodan_chatbotui = list(set(scan_targets(shodan_prompt)))
        new_sites_chatbotui = await func(shodan_chatbotui)
        new_sites_details += [
            {"url": site, "date": time.time(), "type": detail_type}
            for site in new_sites_chatbotui
        ]
    return new_sites_details


async def main():
    with open("all.json", "r") as f:
        old_details = json.load(f)

    old_valid_details = await filter_valid_details(old_details)
    new_details = await new_sites_details()

    old_valid_urls = set(detail["url"] for detail in old_valid_details)
    new_details = [
        detail for detail in new_details if detail["url"] not in old_valid_urls
    ]

    output_details = new_details + old_valid_details
    valid_details = new_details + old_details

    with open("all.json", "w") as f:
        json.dump(valid_details, f, indent=2)
    with open("valid.json", "w") as f:
        json.dump(output_details, f, indent=2)


    recent_list = "".join(
        "- {}\n".format(detail["url"]) for detail in output_details[:5]
    )
    all_list = "".join("- {}\n".format(detail["url"]) for detail in output_details)

    with open("README.md", "w") as f:
        f.write(TEMPLATE.format(recent=recent_list, all=all_list))


if __name__ == "__main__":
    asyncio.run(main())
