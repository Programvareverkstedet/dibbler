{
  description = "Dibbler samspleisebod";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable-small";
    flake-utils.url = "github:numtide/flake-utils";
    devenv.url = "github:cachix/devenv";
  };

  nixConfig = {
    extra-trusted-public-keys = [
      "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw="
    ];
    extra-substituters = [
      "https://devenv.cachix.org"
    ];
  };

  outputs = { self, ... } @ inputs:
    inputs.flake-utils.lib.eachDefaultSystem (system: let
      pkgs = inputs.nixpkgs.legacyPackages.${system};
      inherit (pkgs) lib;
    in {

      packages = {
        default = self.packages.${system}.dibbler;

        dibbler = pkgs.python311Packages.callPackage ./nix/dibbler.nix { };
        skrot-vm = self.nixosConfigurations.skrot.config.system.build.vm;

        # devenv cruft
        devenv-up = self.devShells.${system}.default.config.procfileScript;
        devenv-test = self.devShells.${system}.default.config.test;
      };

      devShells = {
        default = self.devShells.${system}.dibbler;
        dibbler = inputs.devenv.lib.mkShell {
          inherit inputs pkgs;
          modules = [({ config, ... }: {
            # https://devenv.sh/reference/options/

            enterShell = ''
              if [[ ! -f config.ini ]]; then
                  cp -v example-config.ini config.ini
              fi

              export REPO_ROOT=$(realpath .) # used by mkPythonEditablePackage
              export DIBBLER_CONFIG_FILE=$(realpath config.ini)
              export DIBBLER_DATABASE_URL=postgresql://dibbler:hunter2@/dibbler?host=${config.env.PGHOST}
            '';

            packages = [

              /* self.packages.${system}.dibbler */
              (pkgs.python311Packages.mkPythonEditablePackage {
                inherit (self.packages.${system}.dibbler)
                  pname version
                  build-system dependencies;
                scripts = (lib.importTOML ./pyproject.toml).project.scripts;
                root = "$REPO_ROOT";
              })

              pkgs.python311Packages.black
              pkgs.ruff
            ];

            services.postgres = {
              enable = true;
              initialDatabases = [
                {
                  name = "dibbler";
                  user = "dibbler";
                  pass = "hunter2";
                }
              ];
            };

          })];
        };
      };

    })

    //

    {
      # Note: using the module requires that you have applied the
      #       overlay first
      nixosModules.default = import ./nix/module.nix;

      images.skrot = self.nixosConfigurations.skrot.config.system.build.sdImage;

      nixosConfigurations.skrot = inputs.nixpkgs.lib.nixosSystem {
        system = "aarch64-linux";
        modules = [
          (inputs.nixpkgs + "/nixos/modules/installer/sd-card/sd-image-aarch64.nix")
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
