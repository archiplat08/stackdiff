"""Integration tests for the policy CLI sub-command."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from stackdiff.cli_policy import build_parser, _cmd_policy


PLAN_CREATE = textwrap.dedent("""\
  Terraform will perform the following actions:

    # aws_instance.web will be created
    + resource "aws_instance" "web" {
      }

  Plan: 1 to add, 0 to change, 0 to destroy.
""")

PLAN_DESTROY = textwrap.dedent("""\
  Terraform will perform the following actions:

    # aws_instance.web will be destroyed
    - resource "aws_instance" "web" {
      }

  Plan: 0 to add, 0 to change, 1 to destroy.
""")

PLAN_IAM = textwrap.dedent("""\
  Terraform will perform the following actions:

    # aws_iam_role.deployer will be updated in-place
    ~ resource "aws_iam_role" "deployer" {
      }

  Plan: 0 to add, 1 to change, 0 to destroy.
""")


@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    return tmp_path


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


def test_policy_clean_plan_exits_zero(plan_dir):
    f = _write(plan_dir, "create.txt", PLAN_CREATE)
    parser = build_parser()
    args = parser.parse_args(["policy", str(f), "--no-destroy"])
    rc = args.func(args)
    assert rc == 0


def test_policy_destroy_plan_exits_two(plan_dir):
    f = _write(plan_dir, "destroy.txt", PLAN_DESTROY)
    parser = build_parser()
    args = parser.parse_args(["policy", str(f), "--no-destroy"])
    rc = args.func(args)
    assert rc == 2


def test_policy_warn_iam_exits_one(plan_dir, capsys):
    f = _write(plan_dir, "iam.txt", PLAN_IAM)
    parser = build_parser()
    args = parser.parse_args(["policy", str(f), "--warn-iam"])
    rc = args.func(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "WARN" in out


def test_policy_all_rules_applied(plan_dir):
    f = _write(plan_dir, "destroy.txt", PLAN_DESTROY)
    parser = build_parser()
    args = parser.parse_args(["policy", str(f), "--all-rules"])
    rc = args.func(args)
    assert rc == 2


def test_policy_no_flags_uses_defaults(plan_dir):
    """With no rule flags, defaults apply; a destroy plan should still block."""
    f = _write(plan_dir, "destroy.txt", PLAN_DESTROY)
    parser = build_parser()
    args = parser.parse_args(["policy", str(f)])
    rc = args.func(args)
    assert rc == 2
