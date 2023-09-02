{
  description = "Dibbler samspleisebod";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in {
      packages = {
        default = self.packages.${system}.dibbler;
        dibbler = pkgs.callPackage ./nix/dibbler.nix {
          python3Packages = pkgs.python311Packages;
        };
      };

      apps = {
        default = self.apps.${system}.dibbler;
        dibbler = flake-utils.lib.mkApp {
          drv = self.packages.${system}.dibbler;
        };
      };

      devShells = {
        default = self.devShells.${system}.dibbler;
        dibbler = pkgs.mkShell {
          packages = with pkgs; [
            python311Packages.black
            ruff
          ];
        };
      };
    })

    //

    {
      # Note: using the module requires that you have applied the
      #       overlay first
      nixosModules.default = import ./nix/module.nix;

      images.skrot = self.nixosConfigurations.skrot.config.system.build.sdImage;

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
    };
}
