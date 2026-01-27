{
  description = "Dibbler samspleisebod";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }: let
    inherit (nixpkgs) lib;

    systems = [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];

    forAllSystems = f: lib.genAttrs systems (system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in f system pkgs);
  in {
      apps = let
        mkApp = program: description: {
          type = "app";
          program = toString program;
          meta = {
            inherit description;
          };
        };
        mkVm = name: mkApp "${self.nixosConfigurations.${name}.config.system.build.vm}/bin/run-nixos-vm";
      in forAllSystems (system: pkgs: {
        default = self.apps.${system}.dibbler;
        dibbler = let
          app = pkgs.writeShellApplication {
            name = "dibbler-with-default-config";
            runtimeInputs = [ self.packages.${system}.dibbler ];
            text = ''
              dibbler -c ${./example-config.toml} "$@"
            '';
          };
        in mkApp (lib.getExe app) "Run the dibbler cli with its default config against an SQLite database";
        vm = mkVm "vm" "Start a NixOS VM with dibbler installed in kiosk-mode";
        vm-non-kiosk = mkVm "vm-non-kiosk" "Start a NixOS VM with dibbler installed in nonkiosk-mode";
      });

      nixosModules.default = import ./nix/module.nix;

      nixosConfigurations = {
        vm = import ./nix/nixos-configurations/vm.nix { inherit self nixpkgs; };
        vm-non-kiosk = import ./nix/nixos-configurations/vm-non-kiosk.nix { inherit self nixpkgs; };
      };

      overlays = {
        default = self.overlays.dibbler;
        dibbler = final: prev: {
          inherit (self.packages.${prev.stdenv.hostPlatform.system}) dibbler;
        };
      };

      devShells = forAllSystems (system: pkgs: {
        default = self.devShells.${system}.dibbler;
        dibbler = pkgs.callPackage ./nix/shell.nix {
          python = pkgs.python313;
        };
      });

      packages = forAllSystems (system: pkgs: {
        default = self.packages.${system}.dibbler;
        dibbler = pkgs.callPackage ./nix/package.nix {
          python3Packages = pkgs.python313Packages;
        };
      });
    };
}
