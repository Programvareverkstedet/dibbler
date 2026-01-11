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
python -m dibbler -c example-config.ini seed-data
python -m dibbler -c example-config.ini loop
```

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

nix run .# -- --config example-config.ini create-db
nix run .# -- --config example-config.ini seed-data
nix run .# -- --config example-config.ini loop
```
