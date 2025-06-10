{
  mkShell,
  python3,
  ruff,
  uv,
}:

mkShell {
  packages = [
    ruff
    uv
    (python3.withPackages (ps: with ps; [
      # brother-ql
      # matplotlib
      psycopg2
      # python-barcode
      sqlalchemy
      sqlparse

      pytest
      pytest-cov
    ]))
  ];
}
