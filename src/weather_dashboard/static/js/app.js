/**
 * Controlador da página: busca dados no backend (nunca direto no OpenWeatherMap) e renderiza
 * usando apenas textContent/createElement — nenhum dado externo passa por innerHTML.
 */
import {
  addRecentCity,
  capitalize,
  formatDay,
  formatTemperature,
  formatVersion,
  formatWindSpeed,
  iconUrl,
} from "./format.js";

const RECENT_KEY = "weather-dashboard:recent-cities";
const DEFAULT_CITY = "São Paulo";

const elements = {
  form: document.getElementById("search-form"),
  input: document.getElementById("city-input"),
  status: document.getElementById("status"),
  version: document.getElementById("app-version"),
  results: document.getElementById("results"),
  recent: document.getElementById("recent-cities"),
  current: {
    city: document.getElementById("current-city"),
    observed: document.getElementById("current-observed"),
    icon: document.getElementById("current-icon"),
    temperature: document.getElementById("current-temperature"),
    description: document.getElementById("current-description"),
    feelsLike: document.getElementById("current-feels-like"),
    minMax: document.getElementById("current-min-max"),
    humidity: document.getElementById("current-humidity"),
    wind: document.getElementById("current-wind"),
    pressure: document.getElementById("current-pressure"),
  },
  forecastList: document.getElementById("forecast-list"),
};

let activeRequest = null;

// localStorage pode estar indisponível (modo privado, dados bloqueados): nunca é essencial.
function loadRecentCities() {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function saveRecentCities(cities) {
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(cities));
  } catch {
    // Preferência de conveniência — ignorar falhas de armazenamento.
  }
}

async function fetchJson(path, city, signal) {
  const url = `${path}?${new URLSearchParams({ city })}`;
  const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Não foi possível obter os dados.";
    throw new Error(detail);
  }
  return body;
}

function setStatus(message, kind = "info") {
  elements.status.textContent = message;
  elements.status.dataset.kind = kind;
  elements.status.hidden = !message;
}

function setIcon(img, code, description) {
  const src = iconUrl(code);
  img.hidden = !src;
  if (src) {
    img.src = src;
    img.alt = description;
  }
}

function renderCurrent(weather) {
  const c = elements.current;
  const observed = new Date(weather.observed_at);
  c.city.textContent = `${weather.city}, ${weather.country}`;
  c.observed.textContent = `Atualizado às ${observed.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  })} (horário local)`;
  c.observed.dateTime = weather.observed_at;
  setIcon(c.icon, weather.icon, capitalize(weather.description));
  c.temperature.textContent = formatTemperature(weather.temperature);
  c.description.textContent = capitalize(weather.description);
  c.feelsLike.textContent = formatTemperature(weather.feels_like);
  c.minMax.textContent = `${formatTemperature(weather.temp_min)} / ${formatTemperature(weather.temp_max)}`;
  c.humidity.textContent = `${weather.humidity}%`;
  c.wind.textContent = formatWindSpeed(weather.wind_speed);
  c.pressure.textContent = `${weather.pressure} hPa`;
}

function createForecastItem(day) {
  const item = document.createElement("li");
  item.className = "forecast-day";

  const title = document.createElement("h3");
  title.textContent = formatDay(day.day);

  const icon = document.createElement("img");
  icon.width = 64;
  icon.height = 64;
  setIcon(icon, day.icon, capitalize(day.description));

  const description = document.createElement("p");
  description.className = "forecast-description";
  description.textContent = capitalize(day.description);

  const temps = document.createElement("p");
  temps.className = "forecast-temps";
  const max = document.createElement("span");
  max.className = "temp-max";
  max.textContent = formatTemperature(day.temp_max);
  max.title = "Máxima";
  const min = document.createElement("span");
  min.className = "temp-min";
  min.textContent = formatTemperature(day.temp_min);
  min.title = "Mínima";
  temps.append(max, " / ", min);

  const humidity = document.createElement("p");
  humidity.className = "forecast-humidity";
  humidity.textContent = `Umidade ${day.humidity}%`;

  item.append(title, icon, description, temps, humidity);
  return item;
}

function renderForecast(forecast) {
  elements.forecastList.replaceChildren(...forecast.days.map(createForecastItem));
}

function renderRecentCities(cities) {
  const buttons = cities.map((city) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chip";
    button.textContent = city;
    button.addEventListener("click", () => {
      elements.input.value = city;
      searchCity(city);
    });
    return button;
  });
  elements.recent.replaceChildren(...buttons);
  elements.recent.hidden = cities.length === 0;
}

async function searchCity(rawCity) {
  const city = rawCity.trim();
  if (!city) {
    setStatus("Digite o nome de uma cidade.", "error");
    elements.input.focus();
    return;
  }

  // Cancela a busca anterior para que uma resposta lenta não sobrescreva a mais recente.
  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;

  setStatus(`Buscando clima de ${city}…`);
  elements.results.setAttribute("aria-busy", "true");

  try {
    const [current, forecast] = await Promise.all([
      fetchJson("/api/weather/current", city, controller.signal),
      fetchJson("/api/weather/forecast", city, controller.signal),
    ]);
    renderCurrent(current);
    renderForecast(forecast);
    elements.results.hidden = false;
    setStatus("");

    const recent = addRecentCity(loadRecentCities(), current.city);
    saveRecentCities(recent);
    renderRecentCities(recent);
  } catch (error) {
    if (error.name === "AbortError") return;
    setStatus(error.message || "Erro inesperado. Tente novamente.", "error");
  } finally {
    if (activeRequest === controller) {
      elements.results.removeAttribute("aria-busy");
      activeRequest = null;
    }
  }
}

// Selo de versão: detalhe discreto para suporte. Se /health falhar, o selo só fica oculto.
async function loadVersion() {
  try {
    const response = await fetch("/health", { headers: { Accept: "application/json" } });
    if (!response.ok) return;
    const label = formatVersion((await response.json()).version);
    if (label) {
      elements.version.textContent = label;
      elements.version.hidden = false;
    }
  } catch {
    // Sem versão visível não é um erro para o usuário.
  }
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  searchCity(elements.input.value);
});

loadVersion();

const recentCities = loadRecentCities();
renderRecentCities(recentCities);
searchCity(recentCities[0] ?? DEFAULT_CITY);
