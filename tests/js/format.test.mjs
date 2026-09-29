// Testes das funções puras do frontend. Executar com: node --test tests/js/
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  addRecentCity,
  capitalize,
  formatDay,
  formatTemperature,
  formatVersion,
  formatWindSpeed,
  iconUrl,
} from "../../src/weather_dashboard/static/js/format.js";

describe("formatVersion", () => {
  it("prefixes semantic versions with v", () => {
    assert.equal(formatVersion("1.1.0"), "v1.1.0");
    assert.equal(formatVersion("2.0.0-rc.1"), "v2.0.0-rc.1");
  });

  it("keeps the dev fallback as is", () => {
    assert.equal(formatVersion("dev"), "dev");
  });

  it("returns null for anything unexpected", () => {
    for (const value of [undefined, null, 1, "", "v1.0.0", "1.0", "<b>1.0.0</b>"]) {
      assert.equal(formatVersion(value), null);
    }
  });
});

describe("formatTemperature", () => {
  it("rounds to the nearest integer", () => {
    assert.equal(formatTemperature(24.6), "25°C");
    assert.equal(formatTemperature(-3.4), "-3°C");
  });

  it("never renders negative zero", () => {
    assert.equal(formatTemperature(-0.2), "0°C");
  });
});

describe("formatWindSpeed", () => {
  it("converts m/s to km/h", () => {
    assert.equal(formatWindSpeed(10), "36 km/h");
    assert.equal(formatWindSpeed(0), "0 km/h");
  });
});

describe("formatDay", () => {
  it("formats an ISO date without shifting the day", () => {
    assert.match(formatDay("2026-09-29"), /29\/09$/);
  });

  it("includes the weekday", () => {
    assert.match(formatDay("2026-09-29").toLowerCase(), /^ter/);
  });
});

describe("iconUrl", () => {
  it("builds the official icon URL for valid codes", () => {
    assert.equal(iconUrl("01d"), "https://openweathermap.org/img/wn/01d@2x.png");
    assert.equal(iconUrl("10n"), "https://openweathermap.org/img/wn/10n@2x.png");
  });

  it("returns null for unexpected codes", () => {
    for (const code of ["", "1d", "01x", '01d"onerror="x', "../evil"]) {
      assert.equal(iconUrl(code), null);
    }
  });
});

describe("capitalize", () => {
  it("uppercases the first letter", () => {
    assert.equal(capitalize("céu limpo"), "Céu limpo");
  });

  it("handles empty input", () => {
    assert.equal(capitalize(""), "");
  });
});

describe("addRecentCity", () => {
  it("puts the new city first", () => {
    assert.deepEqual(addRecentCity(["Curitiba"], "Recife"), ["Recife", "Curitiba"]);
  });

  it("deduplicates ignoring case", () => {
    assert.deepEqual(addRecentCity(["Recife", "curitiba"], "Curitiba"), ["Curitiba", "Recife"]);
  });

  it("limits the list size", () => {
    const result = addRecentCity(["a", "b", "c"], "d", 3);
    assert.deepEqual(result, ["d", "a", "b"]);
  });

  it("does not mutate the original list", () => {
    const original = ["Recife"];
    addRecentCity(original, "Natal");
    assert.deepEqual(original, ["Recife"]);
  });
});
