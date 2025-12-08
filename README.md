[![Coverage](https://pages.pvv.ntnu.no/Projects/dibbler/event-sourcing/coverage/badge.svg)](https://pages.pvv.ntnu.no/Projects/dibbler/event-sourcing/coverage)

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
python -m dibbler -c example-config.ini create-db
python -m dibbler -c example-config.ini loop
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

### Bygge nytt image

For å bygge et image trenger du en builder som takler å bygge for arkitekturen du skal lage et image for.

(Eller be til gudene om at cross compile funker)

Flaket exposer en modul som autologger inn med en bruker som automatisk kjører dibbler, og setter opp et minimalistisk miljø.

Før du bygger imaget burde du kopiere og endre `example-config.ini` lokalt til å inneholde instillingene dine. **NB: Denne kommer til å ligge i nix storen, ikke si noe her som du ikke vil at moren din skal høre.**

Du kan også endre hvilken config-fil som blir brukt direkte i pakken eller i modulen.

Se eksempelet for hvordan skrot er satt opp i `flake.nix` og `nix/skrott.nix`

### Bygge image for skrot

Skrot har et image definert i flake.nix:

1. endre `example-config.ini`
2. `nix build .#images.skrot`
3. ???
4. non-profit
