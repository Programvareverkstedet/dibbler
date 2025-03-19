{
  mkShell,
  python3Packages,
  ruff,
}:

mkShell {
  packages = [
    python3Packages.black
    ruff
  ];
}
