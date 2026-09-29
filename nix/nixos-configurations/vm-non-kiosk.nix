{ self, nixpkgs, ... }:
nixpkgs.lib.nixosSystem {
  system = "x86_64-linux";
  pkgs = import nixpkgs {
    system = "x86_64-linux";
    overlays = [
      self.overlays.dibbler
    ];
  };
  modules = [
    "${nixpkgs}/nixos/modules/virtualisation/qemu-vm.nix"
    "${nixpkgs}/nixos/tests/common/user-account.nix"

    self.nixosModules.default

    ({ config, lib, pkgs, ... }: {
      system.stateVersion = config.system.nixos.release;
      virtualisation.graphics = false;

      users.motd = ''
        =================================
        Welcome to the dibbler non-kiosk vm!

        Try running:
            ${config.services.dibbler.package.meta.mainProgram} loop

        Password for dibbler is 'dibbler'

        To exit, press Ctrl+A, then X
        =================================
      '';

      users.users.dibbler = {
        isNormalUser = true;
        password = "dibbler";
        extraGroups = [ "wheel" ];
      };

      services.getty.autologinUser = "dibbler";

      programs.vim = {
        enable = true;
        defaultEditor = true;
      };

      services.postgresql.enable = true;

      services.dibbler = {
        enable = true;
        createLocalDatabase = true;
      };

      systemd.services.dibbler-seed-database = {
        description = "Dibbler database seeding";
        wantedBy = [ "default.target" ];
        requires = [ "dibbler-setup-database.service" ];
        after = [ "dibbler-setup-database.service" ];
        before = [ "dibbler-screen-session.service" ];
        unitConfig = {
          ConditionPathExists = "!/var/lib/dibbler/.db-seed-done";
        };
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${lib.getExe config.services.dibbler.package} --config /etc/dibbler/dibbler.toml seed-data";
          ExecStartPost = "${lib.getExe' pkgs.coreutils "touch"} /var/lib/dibbler/.db-seed-done";
          StateDirectory = "dibbler";
          User = "dibbler";
          Group = "dibbler";
        };
      };
    })
  ];
}
