import os
import re
import subprocess
from typing import Optional

from cpk.utils.misc import run_cmd
from cpk.types import GitRepositoryOrigin, GitRepositoryIndex, GitRepositoryVersion, GitRepository


def get_repo_info(path: str) -> GitRepository:
    path = os.path.join(path, '.git')
    if not os.path.exists(path):
        return GitRepository.default()
    # ---
    # get repo info
    # - sha
    try:
        sha = run_cmd(["git", "--git-dir", f'"{path}"',
                       "rev-parse", "HEAD"])[0]
    except subprocess.CalledProcessError as e:
        if e.returncode == 128:
            # empty repository
            return GitRepository.default()
    # - branch
    branch = run_cmd(["git", "--git-dir", f'"{path}"',
                      "rev-parse", "--abbrev-ref", "HEAD"])[0]
    # - remote
    origin_url = run_cmd(["git", "--git-dir", f'"{path}"',
                          "config", "--get", "remote.origin.url"])[0]
    if origin_url.endswith(".git"):
        origin_url = origin_url[:-4]
    if origin_url.endswith("/"):
        origin_url = origin_url[:-1]
    repo = origin_url.split("/")[-1]
    # - info about current git INDEX
    nmodified = len(
        run_cmd(["git", "--git-dir", f'"{path}"',
                 "status", "--porcelain", "--untracked-files=no"]))
    nadded = len(run_cmd(["git", "--git-dir", f'"{path}"', "status", "--porcelain"]))
    clean = abs(nmodified) + abs(nadded) == 0
    # - head/closest git tag
    head_tag = run_cmd(
        [
            "git",
            "--git-dir",
            f'"{path}"',
            "describe",
            "--exact-match",
            "--tags",
            "HEAD",
            "2>/dev/null",
            "||",
            ":",
        ]
    )
    head_tag = head_tag[0] if (head_tag and clean) else None
    closest_tag = run_cmd(["git", "--git-dir", f'"{path}"', "tag"])
    closest_tag = closest_tag[-1] if closest_tag else None
    # return info
    return GitRepository(
        name=repo,
        sha=sha,
        branch=branch,
        present=True,
        detached=branch == "HEAD",
        version=GitRepositoryVersion(
            head=head_tag,
            closest=closest_tag
        ),
        origin=GitRepositoryOrigin(
            url=origin_url,
            url_https=remote_url_to_https(origin_url),
            organization=remote_url_to_organization(origin_url)
        ),
        index=GitRepositoryIndex(
            clean=clean,
            num_added=nadded,
            num_modified=nmodified
        )
    )


def remote_url_to_https(remote_url: str) -> str:
    ssh_pattern = "git@([^:]+):([^/]+)/(.+)"
    res = re.search(ssh_pattern, remote_url, re.IGNORECASE)
    if res:
        return f"https://{res.group(1)}/{res.group(2)}/{res.group(3)}"
    return remote_url


def remote_url_to_organization(remote_url: str) -> Optional[str]:
    remote_url = remote_url_to_https(remote_url)
    https_pattern = "http[s]?://[^/]+/([^/]+)/.+"
    res = re.search(https_pattern, remote_url, re.IGNORECASE)
    if res:
        return res.group(1)
    return None
