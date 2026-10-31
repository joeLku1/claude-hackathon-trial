# Publish the first GitHub release

The code is prepared for `joeLku1/claude-hackathon-trial`. The connected GitHub integration returned HTTP 403, “Resource not accessible by integration,” when creating a Git tree. No branch, commit, pull request, tag, or release was written to GitHub.

## Finish through ChatGPT

Check the connected GitHub integration's access to this repository and enable repository content writes (and workflow writes for `.github/workflows/release.yml`). Then ask ChatGPT to resume publishing this package. Do not paste access tokens into chat.

## Or publish with your own Git client

1. Clone `https://github.com/joeLku1/claude-hackathon-trial.git` to your computer.
2. Copy the contents of the package's `plotcraft-0.1.0` folder into the clone, including `.github` and `.gitignore`. Keep the clone's `.git` directory intact. The `dist` folder is ignored.
3. In the clone, run:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
git add .
git commit -m "Build Plotcraft v0.1.0 live chart design studio"
git push origin main
```

4. Open the repository's Actions tab. The supplied workflow tests Python 3.10 and 3.12, runs the browser smoke flow, builds source/wheel packages, and publishes **v0.1.0** only if all tests pass. Review any failed job before trying to release.

The workflow needs GitHub Actions enabled and a token allowed to write repository contents. It uses the repository's built-in `GITHUB_TOKEN`; no personal token is embedded in the code. It does not change repository permissions. Existing v0.1.0 releases are preserved.

Browser screenshots are uploaded as workflow artifacts. The browser smoke flow has not been run in the build environment because its Chromium download was blocked. Do not call that check passing until Actions reports success.
