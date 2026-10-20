// commitlint: checks that commit messages follow Conventional Commits.
// Runs in CI (.github/workflows/ci.yml, job "commits") and locally through the
// commit-msg hook in .pre-commit-config.yaml.
//
//   <type>(<scope>): <summary in the imperative, lower case>
//   feat(progress): add body measurement endpoints
//
// Merge commits ("Merge PR #12: ...") are ignored by commitlint's defaults.
export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert", "bench"],
    ],
    // Scopes are a warning, not an error: new modules appear over time.
    "scope-enum": [
      1,
      "always",
      [
        // sidecar modules
        "core", "workouts", "activities", "progress", "gamification", "nutrition", "coach", "ai", "io",
        // desktop
        "desktop", "ui", "electron", "a11y",
        // ops and ml
        "ci", "docker", "build", "release", "ml", "deps", "meta", "repo", "github",
        // docs
        "docs", "dev", "adr", "planning", "members", "contracts",
      ],
    ],
    "header-max-length": [2, "always", 120],
    "body-max-line-length": [1, "always", 100],
    "subject-case": [2, "never", ["start-case", "pascal-case", "upper-case"]],
  },
};
