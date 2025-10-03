# SECRET_KEY Rotation Guide

This project relies on the `SECRET_KEY` environment variable for session security and cryptographic signing. Follow the steps below to manage and rotate the key safely.

## Generate a New Key
1. SSH into the server or workstation that manages the deployment.
2. Generate a new random key. A recommended command is:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```
3. Copy the generated value.

## Update Environment Configuration
1. Open the environment configuration (e.g., `.env` file or the deployment tool's variable manager).
2. Replace the current value of `SECRET_KEY` with the newly generated key.
3. Save the changes.

## Apply the Change
1. Restart all services that depend on this application so the new `SECRET_KEY` is loaded. For example:
   ```bash
   systemctl restart gunicorn
   systemctl restart celery
   ```
   Adjust the commands to match your deployment.

## Verify the Deployment
1. Inspect the service logs to ensure they restarted cleanly.
2. Access the application to confirm it is functioning as expected.

## Notes
- Rotating the `SECRET_KEY` invalidates existing sessions. Communicate the maintenance window to users if necessary.
- Never commit the `SECRET_KEY` to version control or share it over insecure channels.
