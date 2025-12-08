[![Coverage](https://pages.pvv.ntnu.no/Projects/dibbler/event-sourcing/coverage/badge.svg)](https://pages.pvv.ntnu.no/Projects/dibbler/event-sourcing/coverage)
[![Test report](https://img.shields.io/badge/status-grab_the_latest_test_report-blue)](https://pages.pvv.ntnu.no/Projects/dibbler/event-sourcing/test-report)

# Dibbler

EDB-system for PVVVV

## Hva er dette?

Dibbler er et system laget av PVVere for PVVere for å byttelåne både matvarer og godis.
Det er designet for en gammeldags VT terminal, og er laget for å være enkelt både å bruke og å hacke på.

Programmet er skrevet i Python, og bruker en sql database for å lagre data.

Samlespleiseboden er satt opp slik at folk kjøper inn varer, og får dibblerkreditt, og så kan man bruke
denne kreditten til å kjøpe ut andre varer. Det er ikke noen form for authentisering, så hele systemet er basert på tillit.
Det er anbefalt å koble en barkodeleser til systemet for å gjøre det enklere å både legge til og kjøpe varer.

## Kom i gang

Installer python, og lag og aktiver et venv. Installer så avhengighetene med `pip install`.

Deretter kan du kjøre programmet med

```console
python -m dibbler -c example-config.toml create-db
python -m dibbler -c example-config.toml seed-data
python -m dibbler -c example-config.toml loop
```

## Prosjektstruktur

Her er en oversikt over prosjektstrukturen og hva de forskjellige mappene og filene gjør.

### `dibbler/models`

I denne mappen ligger databasemodellene. Med få unntak så er hver fil i denne mappen en modell.

Vi bruker for tiden moderne deklarativ SQLAlchemy syntaks for å definere modellene (see [SQLAlchemy - Declarative Mapping Styles](https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html)).

Pass på å ikke putte for mye logikk i modellene, de skal helst bare definere dataene. Konstruktører, hjelpefunksjoner og statisk validering er anbefalt, men unngå dynamisk validering mot databasen - det hører hjemme i `dibbler/queries`.

### `dibbler/queries`

I denne mappen ligger databasespørringer. Disse databasespørringene har etter hvert blitt ganske komplekse da vi ikke lagrer tilstand, men heller deriverer den ut ifra en gående logg av transaksjoner. Her gjøres det også en del validering, både statisk validering av argumenter, men også dynamisk validering mot databasen.

### `dibbler/menus`

Her ligger menydefinisjonene for terminalgrensesnittet. Menyene håndterer brukerinteraksjon og navigasjon.

### `dibbler/lib`

Her finner du hjelpefunksjoner og verktøy som brukes på tvers av prosjektet. Ting som ikke passet inn andre steder.

### `dibbler/subcommands`

Her ligger inngangspunktet for kommandolinjegrensesnittet. Dette er ikke noe vanlige brukere vanligvis vil se da vi har låst dibbler-terminalen til å kjøre terminalgrensesnittet i en evig loop. Det er nyttig for å legge ved ekstra konfigurasjon eller å legge ved vedlikeholdsoppgaver og testverktøy.

### `tests`

Her ligger enhetstester for prosjektet. Testene bruker `pytest` som testløper. Vi tester i all hovedsak databasespørringer og modelllogikk her, da "korrekthet" av terminalgrensesnittet er vanskelig å definere og teste automatisk.

## Nix

> [!NOTE]
> Vi har skrevet nix-kode for å generere en QEMU-VM med tilnærmet produksjonsoppsett.
> Det kjører ikke nødvendigvis noen VM-er i produksjon, og ihvertfall ikke denne VM-en.
> Den er hovedsakelig laget for enkel interaktiv testing, og for å teste NixOS modulen.

Du kan enklest komme i gang med nix-utvikling ved å kjøre test VM-en:

```console
nix run .#vm

# Eller hvis du trenger tilgang til terminalen i VM-en også:
nix run .#vm-non-kiosk
```

Du kan også bygge pakken manuelt, eller kjøre den direkte:

```console
nix build .#dibbler

nix run .# -- --config example-config.toml create-db
nix run .# -- --config example-config.toml seed-data
nix run .# -- --config example-config.toml loop
```

## Produksjonssetting

Se https://wiki.pvv.ntnu.no/wiki/Drift/Dibbler
