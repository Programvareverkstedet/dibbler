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

        config = let
          screen = "${pkgs.screen}/bin/screen";
        in {
          nixpkgs.overlays = [ self.overlays.default ];

          boot = {
            consoleLogLevel = 0;
            enableContainers = false;
            loader.grub.enable = false;
          };

          users = {
            groups.dibbler = { };
            users.dibbler = {
              group = "dibbler";
              isNormalUser = true;
              shell = "${screen} -x dibbler";
            };
          };

          systemd.services.screen-daemon = {
            description = "Dibbler service screen";
            wantedBy = [ "default.target" ];
            serviceConfig = {
              ExecStartPre = "-${screen} -X -S dibbler kill";
              ExecStart = "${screen} -dmS dibbler -O -l /home/dibbler/dibbler/text_based.py";
              ExecStartPost = "${screen} -X -S dibbler width 42 80";
              User = "dibbler";
              Group = "dibbler";
              Type = "forking";
              RemainAfterExit = false;
              Restart = "always";
              RestartSec = "5s";
              SuccessExitStatus = 1;
            }; 
          };

          # https://github.com/NixOS/nixpkgs/issues/84105
          systemd.services."serial-getty@ttyUSB0" = {
            enable = true;
            wantedBy = [ "getty.target" ];
            serviceConfig.Restart = "always";
          };

          services = {
            openssh = {
              enable = true;
              permitRootLogin = "yes";
            };

            getty.autologinUser = lib.mkForce "dibbler";
            udisks2.enable = false;
          };

          networking.firewall.logRefusedConnections = false;
          console.keyMap = "no";
          programs.command-not-found.enable = false;
          i18n.supportedLocales = [ "en_US.UTF-8/UTF-8" ];
          environment.noXlibs = true;

          documentation = {
            info.enable = false;
            man.enable = false;
          };

          security = {
            polkit.enable = lib.mkForce false;
            audit.enable = false;
          };
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
              nameservers = [ "129.241.0.200" "129.241.0.201" ];
              defaultGateway = "129.241.210.129";
              interfaces.eth0 = {
                useDHCP = false;
                ipv4.addresses = [{
                  address = "129.241.210.235";
                  prefixLength = 25;
                }];
              };
            };
            # services.resolved.enable = true;
            # systemd.network.enable = true;
            # systemd.network.networks."30-network" = {
            #   matchConfig.Name = "*";
            #   DHCP = "no";
            #   address = [ "129.241.210.235/25" ];
            #   gateway = [ "129.241.210.129" ];
            # };
          })
        ];
      };
      images.skrot = self.nixosConfigurations.skrot.config.system.build.sdImage;
    };
}
