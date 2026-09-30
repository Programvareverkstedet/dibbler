// See https://allurereport.org/docs/v3/configure/

const dbLabelIs = (value) => ({ labels }) =>
  labels.some((label) => label.name === "db" && label.value === value);

export default {
  name: "Dibbler tests",
  output: "./allure-report",
  environments: {
    sqlite: {
      matcher: dbLabelIs("sqlite"),
      variables: { Database: "SQLite (in-memory)" },
    },
    postgresql: {
      matcher: dbLabelIs("postgresql"),
      variables: { Database: "PostgreSQL" },
    },
  },
};
