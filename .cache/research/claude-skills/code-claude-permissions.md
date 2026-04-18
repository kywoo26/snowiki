# Configure permissions

> Control what Claude Code can access and do with fine-grained permission rules, modes, and managed policies.

Claude Code supports fine-grained permissions so that you can specify exactly what the agent is allowed to do and what it cannot. Permission settings can be checked into version control and distributed to all developers in your organization, as well as customized by individual developers.

## Permission system

Claude Code uses a tiered permission system to balance power and safety:

| Tool type         | Example          | Approval required | "Yes, don't ask again" behavior               |
| :---------------- | :--------------- | :---------------- | :-------------------------------------------- |
| Read-only         | File reads, Grep | No                | N/A                                           |
| Bash commands     | Shell execution  | Yes               | Permanently per project directory and command |
| File modification | Edit/write files | Yes               | Until session end                             |

## Manage permissions

You can view and manage Claude Code's tool permissions with `/permissions`. This UI lists all permission rules and the settings.json file they are sourced from.

* **Allow** rules let Claude Code use the specified tool without manual approval.
* **Ask** rules prompt for confirmation whenever Claude Code tries to use the specified tool.
* **Deny** rules prevent Claude Code from using the specified tool.

Rules are evaluated in order: **deny -> ask -> allow**. The first matching rule wins, so deny rules always take precedence.

## Permission modes

Claude Code supports several permission modes that control how tools are approved. See [Permission modes](/en/permission-modes) for when to use each one. Set the `defaultMode` in your [settings files](/en/settings#settings-files):

| Mode                | Description                                                                                                                                                        |
| :------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `default`           | Standard behavior: prompts for permission on first use of each tool                                                                                                |
| `acceptEdits`       | Automatically accepts file edits and common filesystem commands (`mkdir`, `touch`, `mv`, `cp`, etc.) for paths in the working directory or `additionalDirectories` |
| `plan`              | Plan Mode: Claude can analyze but not modify files or execute commands                                                                                             |
| `auto`              | Auto-approves tool calls with background safety checks that verify actions align with your request. Currently a research preview                                   |
| `dontAsk`           | Auto-denies tools unless pre-approved via `/permissions` or `permissions.allow` rules                                                                              |
| `bypassPermissions` | Skips permission prompts except for writes to protected directories (see warning below)                                                                            |
