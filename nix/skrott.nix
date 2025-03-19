{...}: {
  system.stateVersion = "25.05";
  
  services.dibbler.enable = true;

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
}
