"""Integration test suite for ``repo_manager._groups.repository``."""
from copy import deepcopy
from typing import Dict

import pytest

from repo_manager._groups import repository
from repo_manager._util import HandlerRequest

from ..integration_test_utils import agithub_client  # noqa pylint: disable=unused-import
from ..integration_test_utils import integ_repo  # noqa pylint: disable=unused-import
from ..integration_test_utils import private_integ_repo  # noqa pylint: disable=unused-import
from ..integration_test_utils import INTEG_FLAKE, baseline_wait

pytestmark = [pytest.mark.integ, INTEG_FLAKE]

BASELINE = dict(
    description="What ever could this be?",
    homepage="https://github.com/mattsb42/repo-manager",
    private=False,
    visibility="public",
    has_issues=True,
    has_projects=True,
    has_wiki=True,
    is_template=False,
    default_branch="master",
    allow_squash_merge=True,
    allow_merge_commit=True,
    allow_rebase_merge=True,
    delete_branch_on_merge=False,
)


def compare_repository_data(*, repo, expected: Dict):
    status, actual = repo.get(headers=repository.HEADERS)
    assert status == 200

    for name, value in expected.items():
        assert actual[name] == value
    # Also check default values are reset


def assert_baseline(repo):

    compare_repository_data(repo=repo, expected=BASELINE)


def apply_baseline(repo):
    request = HandlerRequest(arepo=repo, data=deepcopy(BASELINE))

    repository.apply(request)
    baseline_wait()

    assert_baseline(repo)


@pytest.fixture
def from_baseline(integ_repo, agithub_client):
    owner, repo_name = integ_repo.split("/", 1)
    repo = getattr(getattr(agithub_client.repos, owner), repo_name)
    yield repo
    apply_baseline(repo)


def test_repository_baseline(integ_repo, agithub_client):
    owner, repo_name = integ_repo.split("/", 1)
    repo = getattr(getattr(agithub_client.repos, owner), repo_name)
    apply_baseline(repo)
    assert_baseline(repo)


def _build_case(field_name: str, value, description: str) -> pytest.param:
    case_data = deepcopy(BASELINE)
    case_data[field_name] = value
    return pytest.param(case_data, id=description)


def _cases():
    # description
    yield _build_case(
        "description", "and now for something completely different", "change description"
    )

    # homepage
    yield _build_case("homepage", "https://github.com", "change homepage")

    # This only works for GitHub Enterprise Cloud accounts.
    #  I don't have one of those.
    # visibility: [public]/private
    # yield _build_case("visibility", "private", "change visibility to private")

    # has_issues: [true]/false
    yield _build_case("has_issues", False, "disable issues")

    # has_projects: [true]/false
    yield _build_case("has_projects", False, "disable projects")

    # has_wiki: [true]/false
    yield _build_case("has_wiki", False, "disable wiki")

    # is_template: [false]/true
    yield _build_case("is_template", True, "make template")

    # default_branch: [master]/foo
    yield _build_case("default_branch", "foo", "make branch foo the default")

    # allow_squash_merge: [true]/false
    yield _build_case("allow_squash_merge", False, "disable squash merge")

    # allow_merge_commit: [true]/false
    yield _build_case("allow_merge_commit", False, "disable merge commit")

    # allow_rebase_merge: [true]/false
    yield _build_case("allow_rebase_merge", False, "disable rebase merge")

    # delete_branch_on_merge: [false]/true
    yield _build_case("delete_branch_on_merge", True, "delete pull request head branch on merge")

    # :/
    # archived: Note: You cannot unarchive repositories through the API.


@pytest.mark.parametrize("new_config", _cases())
def test_repository(from_baseline, new_config):
    repo = from_baseline

    request = HandlerRequest(arepo=repo, data=deepcopy(new_config))
    repository.apply(request)

    compare_repository_data(repo=repo, expected=new_config)


def test_private_repo_swap(private_integ_repo, agithub_client):
    owner, repo_name = private_integ_repo.split("/", 1)
    repo = getattr(getattr(agithub_client.repos, owner), repo_name)

    private_baseline = dict(
        description="this repo is used to test mattsb42/repo-manager", private=False
    )

    make_public_request = HandlerRequest(arepo=repo, data=deepcopy(private_baseline))
    repository.apply(make_public_request)

    compare_repository_data(repo=repo, expected=private_baseline)

    make_private_data = deepcopy(private_baseline)
    make_private_data["private"] = True
    make_private_request = HandlerRequest(arepo=repo, data=deepcopy(make_private_data))
    repository.apply(make_private_request)

    compare_repository_data(repo=repo, expected=make_private_data)


def test_rename_repository(integ_repo, agithub_client):
    owner, original_name = integ_repo.split("/", 1)
    new_name = original_name + "-name-change"

    repo = getattr(getattr(agithub_client.repos, owner), original_name)
    renamed_repo = getattr(getattr(agithub_client.repos, owner), new_name)

    rename_data = deepcopy(BASELINE)
    rename_data["name"] = new_name
    change_name_request = HandlerRequest(arepo=repo, data=deepcopy(rename_data))
    repository.apply(change_name_request)

    compare_repository_data(repo=renamed_repo, expected=rename_data)

    reset_data = deepcopy(BASELINE)
    reset_data["name"] = original_name
    reset_name_request = HandlerRequest(arepo=renamed_repo, data=deepcopy(reset_data))
    repository.apply(reset_name_request)

    compare_repository_data(repo=repo, expected=reset_data)
