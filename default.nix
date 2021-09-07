{ pkgs ? import <nixos-unstable> { } }:

rec {

  dibbler = pkgs.callPackage ./nix/dibbler.nix { };

}
