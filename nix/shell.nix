{
  mkShell,
  python,
  ruff,
  uv,
}:

mkShell {
  packages = [
    ruff
    uv
    (python.withPackages (ps: with ps; [
      brother-ql
      matplotlib
      libdib
      psycopg2
      python-barcode
      sqlalchemy
    ]))
  ];
}
