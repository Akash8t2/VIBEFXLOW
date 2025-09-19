import asyncio
import shlex
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

import config
from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    # Use asyncio.run() instead of get_event_loop()
    return asyncio.run(install_requirements())


def git():
    REPO_LINK = config.UPSTREAM_REPO
    if config.GIT_TOKEN:
        GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
        TEMP_REPO = REPO_LINK.split("https://")[1]
        UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.GIT_TOKEN}@{TEMP_REPO}"
    else:
        UPSTREAM_REPO = config.UPSTREAM_REPO

    try:
        # ✅ Always pass path
        repo = Repo(".")
        LOGGER(__name__).info("✅ Git repository found.")
    except InvalidGitRepositoryError:
        LOGGER(__name__).warning("⚠️ Not a git repo, skipping git setup on this environment.")
        return
    except GitCommandError:
        LOGGER(__name__).error("❌ Invalid Git Command")
        return

    try:
        origin = repo.remote("origin")
    except ValueError:
        origin = repo.create_remote("origin", UPSTREAM_REPO)

    # Fetch & sync
    try:
        origin.fetch()
        if config.UPSTREAM_BRANCH not in repo.heads:
            repo.create_head(config.UPSTREAM_BRANCH, origin.refs[config.UPSTREAM_BRANCH])
        repo.heads[config.UPSTREAM_BRANCH].set_tracking_branch(origin.refs[config.UPSTREAM_BRANCH])
        repo.heads[config.UPSTREAM_BRANCH].checkout(True)
        origin.pull(config.UPSTREAM_BRANCH)
        LOGGER(__name__).info("✅ Synced with upstream branch.")
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")

    # Reinstall requirements after update
    install_req("pip3 install --no-cache-dir -r requirements.txt")
    LOGGER(__name__).info("📦 Requirements installed & repo updated.")
