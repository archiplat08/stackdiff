# stackdiff

> CLI tool to diff and audit infrastructure state changes across Terraform plan outputs

## Installation

```bash
pip install stackdiff
```

## Usage

Compare two Terraform plan outputs to audit infrastructure state changes:

```bash
# Generate Terraform plan outputs
terraform plan -out=plan.tfplan
terraform show -json plan.tfplan > plan.json

# Diff two plan outputs
stackdiff plan-before.json plan-after.json

# Output as unified diff format
stackdiff plan-before.json plan-after.json --format unified

# Filter by resource type
stackdiff plan-before.json plan-after.json --resource-type aws_instance
```

### Example Output

```
~ aws_instance.web_server
    instance_type: "t2.micro" → "t3.small"
  + tags.Environment: "staging"

+ aws_s3_bucket.logs
- aws_security_group.old_rule
```

## Options

| Flag | Description |
|------|-------------|
| `--format` | Output format: `summary`, `unified`, `json` (default: `summary`) |
| `--resource-type` | Filter results by resource type |
| `--ignore-tags` | Exclude tag-only changes from output |
| `--exit-code` | Return non-zero exit code if differences are found |

## Requirements

- Python 3.8+
- Terraform 1.0+

## License

[MIT](LICENSE)