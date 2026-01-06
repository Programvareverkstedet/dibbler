{ self, nixpkgs, ... }:
nixpkgs.lib.nixosSystem {
  system = "x86_64-linux";
  pkgs = import nixpkgs {
    system = "x86_64-linux";
    overlays = [
      self.overlays.default
    ];
  };
  modules = [
    "${nixpkgs}/nixos/modules/virtualisation/qemu-vm.nix"
    "${nixpkgs}/nixos/tests/common/user-account.nix"

    self.nixosModules.default

    ({ config, ... }: {
      system.stateVersion = config.system.nixos.release;
      virtualisation.graphics = false;

      services.postgresql.enable = true;

      services.dibbler = {
        enable = true;
        createLocalDatabase = true;
        kioskMode = true;
      };
    })
  ];
}
