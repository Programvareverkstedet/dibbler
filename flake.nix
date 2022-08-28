{
  description = "Dibbler samspleisebod";

  inputs.flake-utils.url = "github:numtide/flake-utils";

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system}; in
      {
        packages = rec {
          dibbler = pkgs.callPackage ./nix/dibbler.nix { };
          # dibblerCross = pkgs.pkgsCross.aarch64-multiplatform.callPackage ./nix/dibbler.nix { };
          default = dibbler;
        };
        apps = rec {
          dibbler = flake-utils.lib.mkApp {
            drv = self.packages.${system}.dibbler;
          };
          default = dibbler;
        };
      }
    );
}
