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

## Nix

### Bygge nytt image

For å bygge et image trenger du en builder som takler å bygge for arkitekturen du skal lage et image for.

(Eller be til gudene om at cross compile funker)

Flaket exposer en modul som autologger inn med en bruker som automatisk kjører dibbler, og setter opp et minimalistisk miljø.

Før du bygger imaget burde du endre `conf.py` lokalt til å inneholde instillingene dine. **NB: Denne kommer til å ligge i nix storen, ikke si noe her som du ikke vil at moren din skal høre.**

Du kan også endre hvilken `conf.py` som blir brukt direkte i pakken eller i modulen.

Se eksempelet for hvordan skrot er satt opp i `flake.nix` og `nix/skrott.nix`

### Bygge image for skrot
Skrot har et image definert i flake.nix:

1. endre conf.py
2. `nix build .#images.skrot`
3. ???
4. non-profit
