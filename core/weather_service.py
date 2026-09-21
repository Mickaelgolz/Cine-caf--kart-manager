from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: "Céu limpo", 1: "Predominantemente limpo", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Nevoeiro", 48: "Nevoeiro com geada", 51: "Garoa fraca", 53: "Garoa moderada",
    55: "Garoa forte", 56: "Garoa congelante fraca", 57: "Garoa congelante forte",
    61: "Chuva fraca", 63: "Chuva moderada", 65: "Chuva forte", 66: "Chuva congelante fraca",
    67: "Chuva congelante forte", 71: "Neve fraca", 73: "Neve moderada", 75: "Neve forte",
    77: "Grãos de neve", 80: "Pancadas de chuva fracas", 81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva fortes", 85: "Pancadas de neve fracas", 86: "Pancadas de neve fortes",
    95: "Trovoada", 96: "Trovoada com granizo fraco", 99: "Trovoada com granizo forte",
}


def _get_json(url: str, timeout: int = 8):
    req = urllib.request.Request(url, headers={"User-Agent": "CineCafeKartManager/2.0.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _location_queries(location: str):
    loc = (location or "").strip()
    queries = []
    if loc:
        queries.append("Ingleses do Rio Vermelho" if "ingles" in loc.lower() else loc)
        queries.append(f"{loc}, Florianópolis, Santa Catarina, Brasil")
    if "ingles" in loc.lower():
        queries.extend([
            "Ingleses do Rio Vermelho, Florianópolis, Santa Catarina, Brasil",
            "Florianópolis, Santa Catarina, Brasil",
        ])
    else:
        queries.append("Florianópolis, Santa Catarina, Brasil")
    # mantém ordem removendo duplicados
    return list(dict.fromkeys(queries))


def geocode(location: str):
    last_error = None
    for query in _location_queries(location):
        try:
            params = urllib.parse.urlencode({"name": query, "count": 5, "language": "pt", "format": "json"})
            data = _get_json(f"{GEOCODE_URL}?{params}")
            results = data.get("results") or []
            if results:
                # Prefere SC/Brasil quando a API retornar mais de uma opção.
                result = next(
                    (r for r in results if str(r.get("admin1", "")).lower() in ("santa catarina", "sc") and str(r.get("country_code", "")).upper() == "BR"),
                    results[0],
                )
                label = ", ".join(x for x in [result.get("name"), result.get("admin1"), result.get("country")] if x)
                return float(result["latitude"]), float(result["longitude"]), label
        except Exception as exc:
            last_error = exc
    if last_error:
        raise RuntimeError(f"Não foi possível localizar o kartódromo: {last_error}")
    raise RuntimeError("Não foi possível localizar o kartódromo no serviço meteorológico.")


def local_time():
    # Santa Catarina uses UTC-3; explicit offset also works on Windows without tzdata.
    return datetime.now(timezone(timedelta(hours=-3)))


def fetch_stage_forecast(location: str, started_at=None) -> dict:
    """Consulta a previsão horária do instante atual até 6 horas depois.

    Retorna um dicionário serializável em JSON. A função lança exceção em falhas de
    rede/serviço; a interface decide se isso deve ou não bloquear a bateria.
    """
    lat, lon, resolved = geocode(location)
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m,is_day",
        "forecast_days": 2,
        "timezone": "America/Sao_Paulo",
    })
    data = _get_json(f"{FORECAST_URL}?{params}")
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    reference = started_at or local_time()
    now = reference.replace(minute=0, second=0, microsecond=0, tzinfo=None)

    rows = []
    for i, stamp in enumerate(times):
        try:
            dt = datetime.fromisoformat(stamp)
        except ValueError:
            continue
        delta_h = (dt - now).total_seconds() / 3600
        if 0 <= delta_h < 6:
            raw_code = (hourly.get("weather_code") or [None] * len(times))[i]
            code = int(raw_code) if raw_code is not None else -1
            rows.append({
                "time": stamp,
                "temperature": (hourly.get("temperature_2m") or [None] * len(times))[i],
                "apparent_temperature": (hourly.get("apparent_temperature") or [None] * len(times))[i],
                "precipitation_probability": (hourly.get("precipitation_probability") or [None] * len(times))[i],
                "precipitation": (hourly.get("precipitation") or [None] * len(times))[i],
                "weather_code": code,
                "condition": WEATHER_CODES.get(code, "Condição indisponível"),
                "wind_speed": (hourly.get("wind_speed_10m") or [None] * len(times))[i],
                "wind_gusts": (hourly.get("wind_gusts_10m") or [None] * len(times))[i],
                "is_day": (hourly.get("is_day") or [None] * len(times))[i],
            })

    if not rows:
        raise RuntimeError("O serviço não retornou previsão horária para as próximas 6 horas.")

    return {
        "source": "Open-Meteo",
        "requested_location": location,
        "resolved_location": resolved,
        "latitude": lat,
        "longitude": lon,
        "fetched_at": local_time().strftime("%d/%m/%Y %H:%M:%S"),
        "timezone": "America/Sao_Paulo (UTC-3)",
        "reference_at": reference.isoformat(),
        "hours": rows,
    }


def compact_summary(forecast: dict) -> str:
    rows = forecast.get("hours") or []
    if not rows:
        return "Previsão indisponível"
    probs = [r.get("precipitation_probability") for r in rows if r.get("precipitation_probability") is not None]
    temps = [r.get("temperature") for r in rows if r.get("temperature") is not None]
    max_prob = max(probs) if probs else None
    min_temp = min(temps) if temps else None
    max_temp = max(temps) if temps else None
    rain = f"chuva máx. {max_prob:.0f}%" if max_prob is not None else "chuva sem estimativa"
    temp = f"{min_temp:.0f}–{max_temp:.0f}°C" if min_temp is not None and max_temp is not None else "temperatura indisponível"
    return f"Próximas 6 h: {rain} • {temp}"


# Compatibility for prior UI imports.
fetch_12h_forecast = fetch_stage_forecast
