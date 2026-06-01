# Category: PATH_CONFIGURATION_FAILURE

## Error Signature
- Program installed but command not recognized
- 'xyz' is not recognized as an internal or external command

## Common Causes
- Installation directory missing from PATH environment variable
- Terminal opened before PATH was updated

## Recommended Actions
- Add installation directory to PATH:
  - Windows: System Properties → Environment Variables → Path → Edit
- Restart terminal after installation
- Verify: where <command>

## Diagnostic Commands
- echo %PATH%
- where <executable>

## Confidence Scoring
- High: Command not recognized after confirmed successful install
- Medium: Install succeeded but executable not reachable from terminal
