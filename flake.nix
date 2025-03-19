{
  description = "Dibbler samspleisebod";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, flake-utils }: let
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
      packages = forAllSystems (system: pkgs: {
        default = self.packages.${system}.dibbler;
        dibbler = pkgs.callPackage ./nix/dibbler.nix {
          python3Packages = pkgs.python312Packages;
        };
        skrot = self.nixosConfigurations.skrot.config.system.build.sdImage;
      });

      apps = forAllSystems (system: pkgs: {
        default = self.apps.${system}.dibbler;
        dibbler = flake-utils.lib.mkApp {
          drv = self.packages.${system}.dibbler;
        };
      });

      overlays = {
        default = self.overlays.dibbler;
        dibbler = final: prev: {
          inherit (self.packages.${prev.system}) dibbler;
        };
      };

      devShells = forAllSystems (system: pkgs: {
        default = self.devShells.${system}.dibbler;
        dibbler = pkgs.callPackage ./nix/shell.nix {
          python = pkgs.python312;
        };
      });
      
      # Note: using the module requires that you have applied the overlay first
      nixosModules.default = import ./nix/module.nix;

      nixosConfigurations.skrot = nixpkgs.lib.nixosSystem (rec {
        system = "aarch64-linux";
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ self.overlays.dibbler ];
        };
        modules = [
          (nixpkgs + "/nixos/modules/installer/sd-card/sd-image-aarch64.nix")
          self.nixosModules.default
          ./nix/skrott.nix
        ];
      });
    };
}
