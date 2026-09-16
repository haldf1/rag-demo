# Security Policy

## Supported Versions

Security fixes are applied to the latest version on the `main` branch.

## Reporting a Vulnerability

Please report security issues through GitHub private vulnerability reporting.
If that feature is unavailable, open an issue asking for a private contact
method without including vulnerability details.

Do not publish API keys, access tokens, private documents, or full server logs
in public issues.

## Deployment Notes

- This project is a demonstration and does not include user authentication.
- Do not expose the web service directly to the public internet.
- Keep `.env` local and never commit real API keys.
- Rotate an API key immediately if it may have been exposed.
- Use firewall and network controls when allowing LAN access.
