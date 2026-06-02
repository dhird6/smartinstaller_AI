# Category: PACKAGE_DOWNLOAD_FAILURE

## Error Signature
- Unable to download packages
- Repository unavailable
- Package fetch failed

## Common Causes
- Using offline installer without internet access to repository
- Repository outage or maintenance
- Proxy blocking package repository

## Recommended Actions
- Retry after waiting for repository to recover
- Verify repository access: ping <repo_host>
- Configure proxy for package manager
- Use offline package or mirror

## Diagnostic Commands
- ping <repository_host>
- netstat -ano
- ipconfig /all

## Confidence Scoring
- High: Explicit repository or package download error in logs
- Medium: Installation stalled at package fetch step
