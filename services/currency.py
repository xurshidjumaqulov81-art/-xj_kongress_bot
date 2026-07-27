import aiohttp

CBU_URLS = (
    "https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/",
    "https://cbu.uz/ru/arkhiv-kursov-valyut/json/USD/",
)


async def usd_rate(fallback: float = 12500.0) -> float:
    """Марказий банк курсини олади; API ишламаса захира курс қайтаради."""
    timeout = aiohttp.ClientTimeout(total=10)
    headers = {"User-Agent": "XJ-Congress-Bot/1.0"}

    for url in CBU_URLS:
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        continue
                    data = await response.json(content_type=None)
                    if data and data[0].get("Rate"):
                        return float(str(data[0]["Rate"]).replace(",", "."))
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
            continue

    return float(fallback)

