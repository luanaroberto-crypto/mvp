# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto
adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [1.0.0] - 2026-09-29

### Adicionado

- Cliente assíncrono do OpenWeatherMap com tratamento de erros (404, 401, 5xx, timeout,
  payload inválido)
- Agregação da previsão de 3 em 3 horas em resumos diários
- Endpoints `GET /api/weather/current`, `GET /api/weather/forecast` e `GET /health`
- Validação do nome da cidade e cabeçalhos de segurança (CSP, X-Frame-Options, nosniff)
- Interface web responsiva e acessível, com tema escuro e buscas recentes
- Testes automatizados em Python (pytest) e JavaScript (node:test)
- Pipeline de CI no GitHub Actions (ruff, mypy, pytest com cobertura mínima de 90%)

[1.0.0]: https://github.com/luanaroberto-crypto/mvp/releases/tag/v1.0.0
