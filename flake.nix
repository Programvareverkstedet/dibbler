{
  description = "Dibbler samspleisebod";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    {
      overlays.default = final: prev: {
        dibbler = prev.callPackage ./nix/dibbler.nix { };
      };
    } //

    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
        };
      in {
        packages = rec {
          dibbler = pkgs.dibbler;
          # dibblerCross = pkgs.pkgsCross.aarch64-multiplatform.dibbler;
          default = dibbler;
        };
        apps = rec {
          dibbler = flake-utils.lib.mkApp {
            drv = self.packages.${system}.dibbler;
          };
          default = dibbler;
        };
      }
    ) //

    {
      nixosModules.default = { config, pkgs, ... }: let
        inherit (nixpkgs.legacyPackages."x86_64-linux") lib;
        cfg = config.services.dibbler;
      in {
        options.services.dibbler = {
          package = lib.mkPackageOption pkgs "dibbler" { };
          config = lib.mkOption {
            default = ./conf.py;
          };
        };
        config = {
          nixpkgs.overlays = [ self.overlays.default ];

          users.users.dibbler = {
            group = "dibbler";
            isNormalUser = true;
            shell = "${cfg.package.override { conf = cfg.config; }}/bin/dibbler";
          };
          users.groups.dibbler = { };
          services.getty.autologinUser = lib.mkForce "dibbler";

          i18n.supportedLocales = ["en_US.UTF-8/UTF-8"];
          documentation.info.enable = false;
          documentation.man.enable = false;
          programs.command-not-found.enable = false;
          security.polkit.enable = lib.mkForce false;
          security.audit.enable = false;
          services.udisks2.enable = false;
          boot.enableContainers = false;
          boot.loader.grub.enable = false;

          environment.noXlibs = true;
        };
      };
    } //

    {
      nixosConfigurations.skrot = nixpkgs.lib.nixosSystem {
        system = "aarch64-linux";
        modules = [
          (nixpkgs + "/nixos/modules/installer/sd-card/sd-image-aarch64.nix")
          self.nixosModules.default
          ({...}: {
            system.stateVersion = "22.05";
            networking = {
              hostName = "skrot";
              domain = "pvv.ntnu.no";
            };
          })
        ];
      };
      images.skrot = self.nixosConfigurations.skrot.config.system.build.sdImage;
    };
}
