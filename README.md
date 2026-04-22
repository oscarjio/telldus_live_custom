# Telldus Live (custom) — Home Assistant integration

Nyskriven Home Assistant-integration mot [Telldus Live API](https://developer.telldus.com/wiki/Guides/Telldus%20Live%20API). Skapad för att ersätta den inbyggda `tellduslive`-integrationen som togs bort ur HA core under 2024.

**Allt konfigureras via Home Assistant-appens UI — inga YAML-filer, ingen terminal.**

Entiteter som skapas automatiskt:

- **Sensorer** — en entitet per värde på varje Telldus-sensor (`temperature`, `humidity`, `power`, `illuminance`, vind, regn, UV, tryck, dagg). Korrekta device classes + enheter så långtidsstatistik och grafer fungerar direkt.
- **Switchar** — en entitet per enhet som stöder `TURNON`/`TURNOFF`.

---

## Installera via HACS (rekommenderat)

1. Öppna **HACS** i Home Assistant.
2. Tre-prickmenyn uppe till höger → **Custom repositories**.
3. Lägg till repo-url:en: `https://github.com/oscarjio/telldus_live_custom` och kategori **Integration**. Tryck **Add**.
4. Sök efter **"Telldus Live (custom)"** i HACS-listan och installera.
5. **Starta om Home Assistant** (Inställningar → System → Starta om).
6. Gå till **Inställningar → Enheter och tjänster → Lägg till integration** och sök efter **"Telldus Live (custom)"**.

## Installera manuellt (om du inte har HACS)

1. Ladda ner `telldus_live_custom.zip` från [Releases](https://github.com/oscarjio/telldus_live_custom/releases) (eller zip:en som ligger bredvid denna README).
2. Packa upp i `/config/custom_components/` på Home Assistant-maskinen (Samba, File Editor add-on, eller SSH) så du får:
   ```
   /config/custom_components/telldus_live_custom/
       __init__.py
       api.py
       config_flow.py
       const.py
       coordinator.py
       manifest.json
       sensor.py
       strings.json
       switch.py
       translations/
   ```
3. Starta om Home Assistant.
4. Gå till **Inställningar → Enheter och tjänster → Lägg till integration → "Telldus Live (custom)"**.

---

## Konfigurera i HA-appen

Hela flödet sker i Home Assistants integrationsdialog. Du behöver bara en sak från ett webbläsarfönster: dina applikationsnycklar.

**Steg 1 — skaffa nycklar (en gång):**

- Öppna <https://pa-api.telldus.com/keys/index>, logga in med ditt Telldus-konto.
- Klicka **Generate a private API key**, fyll i en valfri titel (t.ex. `Home Assistant`).
- Du ser nu en rad med **Public key** och **Private key**. Låt fliken vara öppen.

**Steg 2 — koppla in i HA:**

- I HA: **Inställningar → Enheter och tjänster → Lägg till integration → Telldus Live (custom)**.
- Klistra in Public key och Private key från steg 1 → **Skicka**.
- HA visar nu en länk till Telldus godkännande-sida. Tryck på länken, logga in om du ombeds, tryck **Yes** för att godkänna.
- Gå tillbaka till HA → **Skicka** igen.
- Klart. Dina sensorer och switchar börjar dyka upp inom en minut.

---

## Hur det fungerar under huven

- Pollar `/json/sensors/list?includeValues=1&includeScale=1&includeUnit=1` och `/json/devices/list` var 60:e sekund (ändra `DEFAULT_SCAN_INTERVAL` i `const.py` om du vill).
- `DataUpdateCoordinator` delar ett API-anrop mellan alla entiteter så du inte rate-limitar dig själv.
- On/off-kommandon (`/json/device/turnOn`, `/turnOff`) triggar en refresh direkt efter.
- OAuth1-signering sker med `oauthlib` i en worker-tråd så HA:s event-loop aldrig blockeras.

---

## Felsökning

| Problem | Lösning |
|---|---|
| `invalid_keys` | Public/private key stämmer inte. Kopiera från samma rad på `pa-api.telldus.com/keys/index`. |
| `not_authorized` | Du tryckte **Skicka** innan du klickat **Yes** i browserfönstret. Tryck tillbaka, gör om auktoriseringen. |
| Integrationen dyker inte upp i "Lägg till integration"-listan | HA laddar custom_components vid uppstart. Starta om HA en gång efter HACS-installationen. |
| Inga sensorer visas | Kolla att din Tellstick är online på <https://live.telldus.com>. Integrationen ser bara det Telldus Live själva ser. |

Full debug-loggning:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.telldus_live_custom: debug
```

---

## Utveckling / kontribuera

```bash
git clone https://github.com/oscarjio/telldus_live_custom.git
cd telldus_live_custom
# Symlinka in i en HA-devmiljö eller kopiera till /config/custom_components/
```

För att göra en release:

1. Bumpa version i `custom_components/telldus_live_custom/manifest.json`.
2. Skapa en GitHub-release med tag `vX.Y.Z`.
3. GitHub Actions zippar integrationen automatiskt och attachar till release.

## Version

v0.1.0 — 2026-04-22
