{ config, pkgs, lib, ... }: let
  cfg = config.services.dibbler;

  format = pkgs.formats.toml { };
in {
  options.services.dibbler = {
    enable = lib.mkEnableOption "dibbler, the little kiosk computer";

    package = lib.mkPackageOption pkgs "dibbler" { };

    screenPackage = lib.mkPackageOption pkgs "screen" { };

    createLocalDatabase = lib.mkEnableOption "" // {
      description = ''
        Whether to set up a local postgres database automatically.

        ::: {.note}
        You must set up postgres manually before enabling this option.
        :::
      '';
    };

    kioskMode = lib.mkEnableOption "" // {
      description = ''
        Whether to let dibbler take over the entire machine.

        This will restrict the machine to a single TTY and make the program unquittable.
        You can still get access to PTYs via SSH and similar, if enabled.
      '';
    };

    limitScreenHeight = lib.mkOption {
      type = with lib.types; nullOr ints.unsigned;
      default = null;
      example = 42;
      description = ''
        If set, limits the height of the screen dibbler uses to the given number of lines.
      '';
    };

    limitScreenWidth = lib.mkOption {
      type = with lib.types; nullOr ints.unsigned;
      default = null;
      example = 80;
      description = ''
        If set, limits the width of the screen dibbler uses to the given number of columns.
      '';
    };

    settings = lib.mkOption {
      description = "Configuration for dibbler";
      default = { };
      type = lib.types.submodule {
        freeformType = format.type;
      };
    };
  };

  config = lib.mkIf cfg.enable (lib.mkMerge [
    {
      services.dibbler.settings = lib.pipe ../example-config.toml [
        builtins.readFile
        builtins.fromTOML
        (lib.mapAttrsRecursive (_: lib.mkDefault))
      ];
    }
    {
      environment.systemPackages = [ cfg.package ];

      environment.etc."dibbler/dibbler.toml".source = format.generate "dibbler.toml" cfg.settings;

      users = {
        users.dibbler = {
          group = "dibbler";
          isNormalUser = true;
        };
        groups.dibbler = { };
      };

      services.dibbler.settings.database.url = lib.mkIf cfg.createLocalDatabase "postgresql://dibbler?host=/run/postgresql";

      services.postgresql = lib.mkIf cfg.createLocalDatabase {
        ensureDatabases = [ "dibbler" ];
        ensureUsers = [{
          name = "dibbler";
          ensureDBOwnership = true;
          ensureClauses.login = true;
        }];
      };

      systemd.services.dibbler-setup-database = lib.mkIf cfg.createLocalDatabase {
        description = "Dibbler database setup";
        wantedBy = [ "default.target" ];
        after = [ "postgresql.service" ];
        unitConfig = {
          ConditionPathExists = "!/var/lib/dibbler/.db-setup-done";
        };
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${lib.getExe cfg.package} --config /etc/dibbler/dibbler.toml create-db";
          ExecStartPost = "${lib.getExe' pkgs.coreutils "touch"} /var/lib/dibbler/.db-setup-done";
          StateDirectory = "dibbler";

          User = "dibbler";
          Group = "dibbler";
        };
      };
    }
    (lib.mkIf cfg.kioskMode {
      boot.kernelParams = [
        "console=tty1"
      ];


      users.users.dibbler = {
        extraGroups = [ "lp" ];
        shell = (pkgs.writeShellScriptBin "login-shell" "${lib.getExe cfg.screenPackage} -x dibbler") // {
          shellPath = "/bin/login-shell";
        };
      };

      services.dibbler.settings.general = {
        quit_allowed = false;
        stop_allowed = false;
      };

      systemd.services.dibbler-screen-session = {
        description = "Dibbler Screen Session";
        wantedBy = [
          "default.target"
        ];
        after = if cfg.createLocalDatabase then [
          "postgresql.service"
          "dibbler-setup-database.service"
        ] else [
          "network.target"
        ];
        serviceConfig = {
          Type = "forking";
          RemainAfterExit = false;
          Restart = "always";
          RestartSec = "5s";
          SuccessExitStatus = 1;

          User = "dibbler";
          Group = "dibbler";

          ExecStartPre = "-${lib.getExe cfg.screenPackage} -X -S dibbler kill";
          ExecStart = let
            screenArgs = lib.escapeShellArgs [
              # -dm creates the screen in detached mode without accessing it
              "-dm"

              # Session name
              "-S"
              "dibbler"

              # Set optimal output mode instead of VT100 emulation
              "-O"

              # Enable login mode, updates utmp entries
              "-l"
            ];

            dibblerArgs = lib.cli.toCommandLineShellGNU { } {
              config = "/etc/dibbler/dibbler.toml";
            };

          in "${lib.getExe cfg.screenPackage} ${screenArgs} ${lib.getExe cfg.package} ${dibblerArgs} loop";
          ExecStartPost =
            lib.optionals (cfg.limitScreenWidth != null) [
              "${lib.getExe cfg.screenPackage} -X -S dibbler width ${toString cfg.limitScreenWidth}"
            ]
            ++ lib.optionals (cfg.limitScreenHeight != null) [
              "${lib.getExe cfg.screenPackage} -X -S dibbler height ${toString cfg.limitScreenHeight}"
            ];
        };
      };

      services.getty.autologinUser = "dibbler";
    })
  ]);
}
