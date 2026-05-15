# DigitalOcean Droplet Operator Runbook

This runbook is for bringing Lemma miners and validators online on DigitalOcean
Droplets. It assumes testnet `netuid 467` unless your subnet operator has
published a different network and netuid.

Use this together with [getting-started.md](getting-started.md),
[vps-safety.md](vps-safety.md), [miner.md](miner.md), and
[validator.md](validator.md). If you already have root-run services and want to
migrate them later, see [service-user-migration.md](service-user-migration.md).

## Local Or Droplets?

Use your local machine for key creation, coldkey custody, registration, staking,
and code review.

Use Droplets for live miner and validator operation when you want realistic
networking and do not want to run Docker locally. Miners get a stable public IP
and validators run Docker/Lean on Linux instead of Docker Desktop.

Do not treat a Droplet as safer than your laptop for secrets. Put only hotkeys
on it.

## Recommended Layout

| Place | Runs | Key material |
| --- | --- | --- |
| Local machine | `btcli` funding, registration, staking, reviews | Coldkeys and hotkeys before copying |
| Miner Droplet | `lemma miner start` | Miner hotkey only |
| Validator Droplet | `lemma validator start`, Docker, Lean cache | Validator hotkey only |

Start with one miner hotkey and one validator. Add more miner hotkeys only after
the single-hotkey path stays online and answers inside the validator window.

## What Agents Can Safely Help With

Tools like Codex can help draft commands, inspect public chain state, review
logs, edit docs, and configure systemd services.

Use caution around custody and live operations:

- Do not paste seed phrases, coldkey passwords, private key files, API keys, or
 bearer tokens into chat.
- Do not let an assistant create or hold your coldkey.
- Do not approve a command that transfers funds, stakes, unstakes, deletes a
 wallet, destroys a Droplet, or opens broad firewall access unless you
 understand the exact effect.
- Prefer asking an assistant to explain a command before you run it.

## Droplet And Firewall Setup

Create Ubuntu Droplets with SSH-key login. Use DigitalOcean Cloud Firewalls or
an equivalent host firewall before exposing services.

Minimum inbound rules:

| Role | Inbound rules |
| --- | --- |
| Miner | SSH from your IP; miner `AXON_PORT` from the public internet so validators can reach it |
| Validator | SSH from your IP |

Keep outbound traffic open unless you have a stricter network policy ready.
Validators and miners need chain RPC, package installs, and git or container
registry access.

DigitalOcean references:

- [Getting started with Droplets](https://docs.digitalocean.com/products/droplets/getting-started/)
- [Getting started with Cloud Firewalls](https://docs.digitalocean.com/products/networking/firewalls/getting-started/)
- [Create a Cloud Firewall](https://docs.digitalocean.com/products/networking/firewalls/how-to/create/)

## Server Bootstrap

Run this once per Droplet as the initial SSH user. It creates a dedicated
`lemma` service user and keeps the checkout under `/opt/lemma`.

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates build-essential docker.io
sudo systemctl enable --now docker

sudo useradd --create-home --shell /bin/bash lemma || true
sudo usermod -aG docker lemma
sudo install -d -o lemma -g lemma /opt/lemma
```

Open a shell as the service user:

```bash
sudo -iu lemma bash -lc '
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=/home/lemma/.local/bin:$PATH
git clone https://github.com/spacetime-tao/lemma.git /opt/lemma
cd /opt/lemma
uv sync --extra btcli
'
```

If the repo already exists, update instead:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
git pull --ff-only
uv sync --extra btcli
'
```

## Keys And Registration

Create, fund, register, and stake from your local machine. Copy only the hotkey
directory to the Droplet. The coldkey private file and seed phrase stay local.

See the hotkey-only copy checklist in [vps-safety.md](vps-safety.md#copy-only-the-hotkey-to-the-vps).

After copying the hotkey, tighten permissions on the Droplet:

```bash
sudo -iu lemma bash -lc 'chmod -R go-rwx ~/.bittensor/wallets'
```

## Miner Droplet

Edit `/opt/lemma/.env`:

```bash
SUBTENSOR_NETWORK=test
NETUID=467
BT_WALLET_COLD=<wallet-name>
BT_WALLET_HOT=<miner-hotkey-name>
AXON_EXTERNAL_IP=<miner-droplet-public-ip>
AXON_PORT=8091
```

Sanity-check:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
uv run lemma doctor
'
```

Install a systemd unit:

```bash
sudo tee /etc/systemd/system/lemma-miner.service >/dev/null <<'EOF'
[Unit]
Description=Lemma miner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lemma
WorkingDirectory=/opt/lemma
Environment=PATH=/home/lemma/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/lemma/.local/bin/uv run lemma miner start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now lemma-miner
sudo journalctl -u lemma-miner -f
```

For multiple miners on one Droplet, the lowest-surprise setup is one working
directory per hotkey, each with its own `.env`, `AXON_PORT`, log stream, and
systemd unit. Lemma's `.env` normally wins over process environment variables, so
do not rely on systemd `Environment=` overrides unless you also set
`LEMMA_PREFER_PROCESS_ENV=1` intentionally.

## Validator Droplet

Edit `/opt/lemma/.env`:

```bash
SUBTENSOR_NETWORK=test
NETUID=467
BT_WALLET_COLD=<wallet-name>
BT_WALLET_HOT=<validator-hotkey-name>
LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest
LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS=8
LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES=17179869184
LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker
```

For production, replace `lemma/lean-sandbox:latest` with the subnet-published
immutable image ref ([toolchain-image-policy.md](toolchain-image-policy.md)).

Build the local sandbox image and start the long-lived worker (mounts the
`lemma-lean-cache` Docker named volume at `/lemma-workspace`):

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
bash scripts/start_lean_docker_worker.sh --update-dotenv
uv run lemma doctor
'
```

Install a systemd unit:

```bash
sudo tee /etc/systemd/system/lemma-validator.service >/dev/null <<'EOF'
[Unit]
Description=Lemma validator
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=simple
User=lemma
WorkingDirectory=/opt/lemma
Environment=PATH=/home/lemma/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/lemma/.local/bin/uv run lemma validator start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now lemma-validator
sudo journalctl -u lemma-validator -f
```

Watch for the per-epoch log line
`epoch theorems=N solved=N earned=X.XXX burn=X.XXX miners_paid=N elapsed=X.XXs`.
The live target is miner forwards completing, Lean verification finishing,
nonzero scored miners, `set_weights`, and emissions moving across repeated
rounds.

## Re-Spin Checklist

Use this when restarting existing Droplets:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
git status --short --branch
git pull --ff-only
uv sync --extra btcli
uv run lemma doctor
'
```

Miner:

```bash
sudo systemctl restart lemma-miner
sudo journalctl -u lemma-miner -n 100 --no-pager
```

Validator:

```bash
sudo systemctl restart lemma-validator
sudo journalctl -u lemma-validator -n 100 --no-pager
```

Record after each run:

- commit SHA;
- Droplet size, region, public IP;
- `.env` pins without secrets;
- miner forward latency;
- validator Lean cold/warm timing and failure reasons;
- scored miner count, `set_weights`, and emission movement.
