{ config, pkgs, lib, ... }: let
  cfg = config.services.dibbler;

  format = pkgs.formats.ini { };
in {
  options.services.dibbler = {
    enable = lib.mkEnableOption "dibbler, the little kiosk computer";

    package = lib.mkPackageOption pkgs "dibbler" { };

    settings = lib.mkOption {
      description = "Configuration for dibbler";
      default = { };
      type = lib.types.submodule {
        freeformType = format.type;
      };
    };
  };

  config = let
    screen = "${pkgs.screen}/bin/screen";
  in lib.mkIf cfg.enable {
    services.dibbler.settings = lib.pipe ../example-config.ini [
      builtins.readFile
      builtins.fromTOML
      (lib.mapAttrsRecursive (_: lib.mkDefault))
    ];

    boot = {
      consoleLogLevel = 0;
      enableContainers = false;
      loader.grub.enable = false;
    };

    users = {
      groups.dibbler = { };
      users.dibbler = {
        group = "dibbler";
        extraGroups = [ "lp" ];
        isNormalUser = true;
        shell = (pkgs.writeShellScriptBin "login-shell" "${screen} -x dibbler") // {shellPath = "/bin/login-shell";};
      };
    };

    systemd.services.screen-daemon = {
      description = "Dibbler service screen";
      wantedBy = [ "default.target" ];
      serviceConfig = {
        ExecStartPre = "-${screen} -X -S dibbler kill";
        ExecStart = let
          config = format.generate "dibbler-config.ini" cfg.settings;
        in "${screen} -dmS dibbler -O -l ${cfg.package}/bin/dibbler --config ${config} loop";
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
    boot.kernelParams = [
      "console=ttyUSB0,9600"
      "console=tty1"
    ];
    systemd.services."serial-getty@ttyUSB0" = {
      enable = true;
      wantedBy = [ "getty.target" ]; # to start at boot
      serviceConfig.Restart = "always"; # restart when session is closed
    };

    services.getty.autologinUser = lib.mkForce "dibbler";
  };
}
