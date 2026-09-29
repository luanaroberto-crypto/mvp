/**
 * Funções puras de formatação e estado — sem acesso ao DOM, para serem testáveis com node:test.
 */

const ICON_CODE = /^\d{2}[dn]$/;
const SEMVER = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;
export const MAX_RECENT_CITIES = 5;

/** Temperatura arredondada em °C, evitando exibir "-0°C". */
export function formatTemperature(celsius) {
  const rounded = Math.round(celsius);
  return `${rounded === 0 ? 0 : rounded}°C`;
}

/** A API devolve vento em m/s; km/h é mais familiar para o público brasileiro. */
export function formatWindSpeed(metersPerSecond) {
  return `${Math.round(metersPerSecond * 3.6)} km/h`;
}

/** "2026-09-29" -> "ter., 29/09". Monta a data em horário local para não deslocar o dia. */
export function formatDay(isoDate, locale = "pt-BR") {
  const [year, month, day] = isoDate.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  const weekday = date.toLocaleDateString(locale, { weekday: "short" });
  const dayMonth = date.toLocaleDateString(locale, { day: "2-digit", month: "2-digit" });
  return `${weekday}, ${dayMonth}`;
}

/** URL do ícone oficial, ou null se o código não tiver o formato esperado (defesa em profundidade). */
export function iconUrl(code) {
  return ICON_CODE.test(code) ? `https://openweathermap.org/img/wn/${code}@2x.png` : null;
}

/** "1.1.0" -> "v1.1.0"; "dev" passa como está; qualquer outra coisa -> null (selo oculto). */
export function formatVersion(version) {
  if (typeof version !== "string") return null;
  if (version === "dev") return "dev";
  return SEMVER.test(version) ? `v${version}` : null;
}

export function capitalize(text) {
  return text ? text.charAt(0).toLocaleUpperCase("pt-BR") + text.slice(1) : "";
}

/** Coloca a cidade no topo da lista, sem duplicar (ignorando maiúsculas) e limitando o tamanho. */
export function addRecentCity(recent, city, max = MAX_RECENT_CITIES) {
  const key = city.toLocaleLowerCase("pt-BR");
  const others = recent.filter((item) => item.toLocaleLowerCase("pt-BR") !== key);
  return [city, ...others].slice(0, max);
}
