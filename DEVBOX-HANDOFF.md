# Devbox handoff

## Location and branch

- Devbox checkout: `/home/dev/src/talon-web`
- Git branch: `main`
- Service: Flask/Gunicorn HTML email-thread processor.

## First use

```bash
cd /home/dev/src/talon-web
git pull --ff-only
docker build -t talon-web:dev .
docker run -d --rm --name talon-web \
  -p 127.0.0.1:5000:5000 \
  --restart unless-stopped \
  talon-web:dev
curl --fail http://127.0.0.1:5000/health
```

The service is deliberately loopback-only. Access it from Windows with:

```powershell
ssh -N -L 5000:127.0.0.1:5000 codex-devbox
```

## Operating notes

- No mailbox credentials are required for the core API; its optional `e2e_tests` Azure/O365 configuration is not copied to the devbox.
- Do not expose port 5000 through the firewall, Tailscale Serve, or a public proxy.
- Stop it with `docker stop talon-web`; remove the image only if you deliberately want to reclaim its build space.
