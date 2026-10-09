# Free-tier demo deployment

This setup keeps the API, background worker, model, and SQLite database together on one Oracle Cloud Infrastructure (OCI) VM. Vercel hosts only the static React UI. Caddy terminates HTTPS for the API hostname and proxies to the API over the private Compose network.

This is a best-effort free-tier demo, not a production availability guarantee. OCI Always Free compute is limited to the tenancy's home region and available capacity; Oracle may reclaim qualifying idle instances. Account signup normally requires a payment card for identity verification. Keep the VM within the current Always Free quotas, and check the OCI console before creating resources.

## 1. Create the OCI VM and free hostname

1. Create or sign in to an OCI Free Tier account. Choose the home region carefully; Always Free compute must be created there. Prefer an Ampere A1 VM if available and keep the tenancy within the published Always Free compute and block-volume limits.
2. Create a VM with a public IPv4 address. Allow inbound TCP 80 and 443 in the OCI network security rules. Restrict SSH (TCP 22) to your current public IP; do not expose port 8000.
3. Register a free DuckDNS subdomain and point its A record to the VM's public IPv4 address. DuckDNS may require updating the record if the VM address changes.
4. Install Docker Engine and the Docker Compose plugin on the VM, then clone this repository there.

References: [OCI Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [OCI Free Tier FAQ](https://www.oracle.com/cloud/free/faq/), [DuckDNS](https://www.duckdns.org/).

## 2. Configure the API host

From the repository root on the VM:

```bash
cp deploy/oracle/.env.example deploy/oracle/.env
chmod 600 deploy/oracle/.env
```

Edit `deploy/oracle/.env` on the VM, setting:

- `API_KEY`: the current organizer-issued key. Do not reuse a key that has been exposed in chat, shell history, or a public repository; request rotation from the organizer if needed.
- `SUPPORT_PASSWORD`: a unique support-console password.
- `API_HOST`: the DuckDNS hostname, without `https://`.
- `DASHBOARD_ORIGINS`: the exact Vercel origin, such as `https://your-project.vercel.app` (no trailing slash). Use a comma-separated list only if multiple known UI origins are needed.

After the DuckDNS A record resolves to the VM, start the API and HTTPS proxy:

```bash
docker compose --env-file deploy/oracle/.env -f deploy/oracle/compose.yaml up --build -d
docker compose --env-file deploy/oracle/.env -f deploy/oracle/compose.yaml ps
```

Caddy obtains and renews the public TLS certificate automatically. Its `/data` volume must remain intact. The API listens only inside the Compose network; the host exposes Caddy on ports 80 and 443.

The SQLite database is stored under the repository's `data/` directory on the VM's boot volume. Back up that directory before rebuilding or replacing the VM. Do not run multiple API replicas against this SQLite file.

## 3. Deploy the UI on Vercel

1. Import the repository into Vercel. Set the project root directory to `frontend`.
2. In Vercel project settings, set `VITE_API_BASE_URL` to `https://<API_HOST>` (no trailing slash), then deploy.
3. Copy the resulting production Vercel origin into `DASHBOARD_ORIGINS` on the VM, then restart the API:

   ```bash
   docker compose --env-file deploy/oracle/.env -f deploy/oracle/compose.yaml up --build -d
   ```

4. Verify `https://<API_HOST>/health` returns a loaded model and the Vercel page reports the API as online.

The `VITE_API_BASE_URL` value is public configuration, not a secret. Never set `API_KEY` or `SUPPORT_PASSWORD` as Vercel frontend build variables: browser bundles are public. The backend keeps those values server-side.

## Free-tier limits and reliability

- OCI free compute is capacity-constrained, must be in the home region, and may be reclaimed if it meets Oracle's idle-instance criteria.
- DuckDNS supplies a hostname, not compute, backups, monitoring, or an availability SLA.
- Vercel Hobby is intended for personal, non-commercial use. Check its current terms and usage limits before using it for a competition/demo.
- A free deployment should not be represented as meeting a guaranteed uptime/SLA requirement. Keep a local Docker deployment available as a fallback.
