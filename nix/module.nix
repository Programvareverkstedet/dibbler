{ config, pkgs, lib, ... }: let
  cfg = config.services.dibbler;
in {
  options.services.dibbler = {
    enable = lib.mkEnableOption "dibbler, the little kiosk computer";
    
    package = lib.mkPackageOption pkgs "dibbler" { };
    
    config = lib.mkOption {
      type = lib.types.path;
      description = "Path to the configuration file.";
      default = ../example-config.ini;
    };
  };

  config = let
    screen = "${pkgs.screen}/bin/screen";
  in lib.mkIf cfg.enable {
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
        shell = ((pkgs.writeShellScriptBin "login-shell" "${screen} -x dibbler") // {shellPath = "/bin/login-shell";});
      };
    };

    systemd.services.screen-daemon = {
      description = "Dibbler service screen";
      wantedBy = [ "default.target" ];
      serviceConfig = {
        ExecStartPre = "-${screen} -X -S dibbler kill";
        ExecStart = "${screen} -dmS dibbler -O -l ${cfg.package}/bin/dibbler --config ${cfg.config} loop";
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
    # environment.noXlibs = true;

    documentation = {
      info.enable = false;
      man.enable = false;
    };

    security = {
      polkit.enable = lib.mkForce false;
      audit.enable = false;
    };
  };
}
