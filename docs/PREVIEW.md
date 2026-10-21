# Open your private working preview

[Open this project in GitHub Codespaces](https://codespaces.new/cbegalla111/sportsMLmodel?quickstart=1)

1. Follow that link and click **Create codespace** if GitHub asks. First launch installs pinned dependencies and imports historical data; subsequent starts reuse the saved workspace.
2. The configured port opens the app in a browser tab after startup. If popups are blocked, use the editor's **Ports** panel → **8765** → **Open in Browser**. Keep **Visibility: Private**. GitHub sign-in and the app password are both required.
3. In the editor, choose **Terminal → Run Task → Preview: open private password file**. Copy the generated password into the app login. This file is in the ignored `runtime/` directory; it must never be committed or shared. If you deleted it after saving your password, use your saved password instead.
4. Put the preview tab beside the editor. CSS, HTML and browser-JavaScript changes reload automatically within about two seconds while the preview tab is visible. For Python changes, run **Preview: restart after Python edits**, refresh the page, and sign in again. Draft form entries are not preserved across a page reload.

This is a real interactive app, using real imported records and explicit missing-data states. It is not a public GitHub Pages site. The embedded pane inside a separate ChatGPT conversation cannot be enabled by repository configuration; that chat has no live-preview integration. The app deliberately blocks framing, so use the browser tab rather than a Simple Browser iframe. A static screenshot can be shown in chat when requested.

## Commands

From the checkout (works outside `/workspace` too):

```bash
bash scripts/install.sh              # First install / refresh
bash scripts/codespaces-start.sh     # Start or reuse private preview
bash scripts/preview.sh status
bash scripts/codespaces-start.sh restart
bash scripts/preview.sh stop
```

Codespaces configuration sets runtime data and the virtual environment to ignored `runtime/` and `.venv/` inside the checkout. Existing cloud tasks keep their previous sibling-directory defaults, preserving all saved records. Port 8765 is forwarded privately; the Codespaces startup script explicitly requests private visibility using GitHub CLI and reports a failure if it cannot confirm it. It never switches a port to public. Secure cookies are enabled for Codespaces HTTPS forwarding, and only its exact configured origin passes the app's browser Origin check. Spoofed forwarded-host headers do not override that configuration.

The startup command is idempotent and logs to `runtime/server.log` and `runtime/refresh.log` in Codespaces. It supervises the app and six-hour data worker. Stop/restart only affects a supervisor launched by this checkout's preview command, preventing accidental termination of unrelated applications. The password is never written into a preview URL, browser source, task output, or Git.

GitHub Codespaces itself has not been provisioned from this cloud task. The portable startup, browser behavior and HTTPS-proxy authentication are validated locally; the first actual Codespaces launch still needs the user to create/open the workspace and confirm the forwarded port is private.

Codespaces storage is separate from this cloud machine. Existing prediction history does not transfer merely by pushing code. To keep your personal ledger, download a private backup from the current workspace and follow [the restore instructions](OPERATIONS.md) into a new directory, then set SPORTSLAB_HOME to that directory and restart. Never commit a private runtime database. New Codespaces installs recover public-source data and hash-matching committed benchmark artifacts; revised upstream history may prevent a benchmark digest from matching, in which case it is withheld. Stop unused codespaces through GitHub; commit/push source changes and keep off-machine data backups before deleting a codespace.
