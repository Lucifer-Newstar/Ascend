// commitlint: checks that commit messages follow Conventional Commits.
// Runs in CI (.github/workflows/ci.yml, job "commits") and locally through the
// commit-msg hook in .pre-commit-config.yaml.
//
//   <type>(<scope>): <summary in the imperative, lower case>
//   feat(progress): add body measurement endpoints
//
// Merge commits are skipped: GitHub's defaults ("Merge pull request ...") by
// commitlint itself, and our lead-merge titles ("Merge PR #12: ...") below.
export default {
  extends: ["@commitlint/config-conventional"],
  ignores: [(message) => /^Merge PR #\d+: /.test(message)],
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
        "sidecar", "db", "core", "workouts", "activities", "progress", "gamification", "nutrition", "coach", "ai", "io",
        // desktop
        "desktop", "shared", "ui", "electron", "a11y",
        // ops and ml
        "ci", "docker", "build", "release", "ml", "deps", "meta", "repo", "github",
        // docs
        "docs", "dev", "adr", "planning", "members", "contracts", "readme", "research",
        // v8 feature areas
        "trainer", "map", "muscles", "library", "today", "game", "backup",
        // Dependabot's ML requirement bumps
        "ml-deps",
      ],
    ],
    "header-max-length": [2, "always", 120],
    "body-max-line-length": [1, "always", 100],
    // A warning like the body rule: the parser treats a line containing "#<word with a digit>"
    // (a colour such as #3e9e7c, or an issue ref) as a footer, so a long prose line can trip it.
    "footer-max-line-length": [1, "always", 100],
    "subject-case": [2, "never", ["start-case", "pascal-case", "upper-case"]],
  },
};
