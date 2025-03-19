{
  mkShell,
  python,
  ruff,
}:

mkShell {
  packages = [
    ruff
    (python.withPackages (ps: with ps; [
      brother-ql
      matplotlib
      psycopg2
      python-barcode
      sqlalchemy
    ]))
  ];
}
