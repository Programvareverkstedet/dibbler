{ pkgs ? import <nixos-unstable> { } }:
{
  dibbler = pkgs.callPackage ./nix/dibbler.nix { };
}
