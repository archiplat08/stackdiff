"""Integration tests for cli_dependency subcommand."""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


PLAN_TEXT = textwrap.dedent("""\
    Terraform will perform the following actions:

      # aws_vpc.main will be created
      + resource "aws_vpc" "main" {
        }

      # aws_subnet.pub will be created
      + resource "aws_subnet" "pub" {
        }

      # aws_instance.web will be created
      + resource "aws_instance" "web" {
        }

    Plan: 3 to add, 0 to change, 0 to destroy.
""")


@pytest.fixture()
def plan_dir(tmp_path: Path) -> Path:
    (tmp_path / "plan.txt").write_text(PLAN_TEXT)
    return tmp_path


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "stackdiff.cli_dependency", "dependency"] + args,
        capture_output=True,
        text=True,
    )


def test_list_nodes_exits_zero(plan_dir: Path):
    result = _run([str(plan_dir / "plan.txt")])
    assert result.returncode == 0


def test_list_nodes_json(plan_dir: Path):
    result = _run([str(plan_dir / "plan.txt"), "--json"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    addresses = {n["address"] for n in data}
    assert "aws_vpc.main" in addresses
    assert "aws_subnet.pub" in addresses


def test_blast_radius_text(plan_dir: Path):
    deps_file = plan_dir / "deps.json"
    deps_file.write_text(json.dumps({
        "aws_subnet.pub": ["aws_vpc.main"],
        "aws_instance.web": ["aws_subnet.pub"],
    }))
    result = _run([
        str(plan_dir / "plan.txt"),
        "--deps", str(deps_file),
        "--blast-radius", "aws_vpc.main",
    ])
    assert result.returncode == 0
    assert "aws_subnet.pub" in result.stdout
    assert "aws_instance.web" in result.stdout


def test_blast_radius_json(plan_dir: Path):
    deps_file = plan_dir / "deps.json"
    deps_file.write_text(json.dumps({"aws_subnet.pub": ["aws_vpc.main"]}))
    result = _run([
        str(plan_dir / "plan.txt"),
        "--deps", str(deps_file),
        "--blast-radius", "aws_vpc.main",
        "--json",
    ])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "blast_radius" in data
    assert "aws_subnet.pub" in data["blast_radius"]


def test_upstream_text(plan_dir: Path):
    deps_file = plan_dir / "deps.json"
    deps_file.write_text(json.dumps({"aws_subnet.pub": ["aws_vpc.main"]}))
    result = _run([
        str(plan_dir / "plan.txt"),
        "--deps", str(deps_file),
        "--upstream", "aws_subnet.pub",
    ])
    assert result.returncode == 0
    assert "aws_vpc.main" in result.stdout


def test_no_downstream_message(plan_dir: Path):
    result = _run([
        str(plan_dir / "plan.txt"),
        "--blast-radius", "aws_instance.web",
    ])
    assert result.returncode == 0
    assert "no downstream" in result.stdout
