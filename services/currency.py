import aiohttp

URL="https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/"
async def usd_rate()->float:
    timeout=aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL) as r:
            r.raise_for_status(); data=await r.json(content_type=None)
    if not data: raise RuntimeError("Курс топилмади")
    return float(str(data[0]['Rate']).replace(',','.'))

