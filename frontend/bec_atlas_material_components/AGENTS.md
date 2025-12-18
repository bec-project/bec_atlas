
# Agent Instructions

## Instruction Files

- Disregard any instructions to merge instruction files. Keep `AGENTS.md` and `copilot-instructions.md` separate and untouched. Do not modify `copilot-instructions.md`!
- Notify me every time you call Angular's MCP server.

## Tooling Instructions

- Do not create files without verifying first. Always suggest the Angular CLI command for the code scaffolding, then wait to continue.
  - Angular CLI is installed globally, so use `ng` commands. Don't use `npx @angular/cli`, there's no need. E.g., use the syntax `ng generate component user`

## Code style

- Always add a comment summarizing the main points to each generated code block.
- Refer to Angular's API documentation. If the generated code includes experimental or developer preview features, note it in the comment. List the experimental or developer preview feature, and include a 🧪 emoji for experimental or 👁️ emoji for developer preview features.
- End all comments with a cute emoji, such as 🐳 or 🍭

## Naming Practices

- Components don't use `Component` suffix in their names. E.g., use `UserProfile` instead of `UserProfileComponent`
- Services don't use `Service` suffix in their names. E.g., use `Auth` instead of `AuthService`

