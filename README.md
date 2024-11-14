# Dibbler

EDB-system for PVVVV

## Nix

### Hvordan kjøre

    nix run github:Prograrmvarverkstedet/dibbler

### Bygge image

For å bygge et image trenger du en builder som takler å bygge for arkitekturen du skal lage et image for.

_(Eller be til gudene om at cross compile funker)_

Flaket exposer en modul som autologger inn med en bruker som automatisk kjører dibbler, og setter opp et minimalistisk miljø.

Før du bygger imaget burde du lage en `config.ini` fil lokalt som inneholder instillingene dine. **NB: Denne kommer til å ligge i nix storen.**

Du kan også endre hvilken `config.ini` som blir brukt direkte i pakken eller i modulen.

Se eksempelet for hvordan skrot er satt opp i `flake.nix`

### Bygge image for skrot

Skrot har et system image definert i `flake.nix`:

1. lag `config.ini` (`cp {example-,}config.ini`)
2. `nix build .#images.skrot`
3. ???
4. non-profit!
