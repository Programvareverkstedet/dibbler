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

      # NOTE: if you spin up this vm first, and then the non-kiosk one,
      #       the non-kiosk one will reuse the same qemu image, and so
      #       the non-kiosk one will not have a password unless it's
      #       also set here.
      users.users.dibbler = {
        isNormalUser = true;
        password = "dibbler";
        extraGroups = [ "wheel" ];
      };

      services.postgresql.enable = true;

      services.dibbler = {
        enable = true;
        createLocalDatabase = true;
        kioskMode = true;
      };
    })
  ];
}
