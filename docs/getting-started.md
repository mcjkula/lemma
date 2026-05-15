# Getting started

End-to-end: **uv** + repo → **keys** → edit `.env` → **miner or validator**. Sections below are copy-paste commands (swap wallet names and paths if yours differ).

- Run `uv run lemma` for command help (same as `uv run lemma --help`).
- After install: `uv run lemma doctor` checks env, config, Lean sandbox worker, and chain RPC.
- **On-chain try:** Lemma runs on **Bittensor testnet** (`--network test`), **netuid 467** — miners can earn **testnet alpha** per subnet rules. **Finney** is **mainnet**; **mainnet alpha** applies only if Lemma (or your target deployment) is registered there with emissions — never confuse network or netuid. The repo is still largely proof-of-concept; direction is in [vision](vision.md).

## Paths at a glance

**Miner:** `uv sync --extra btcli` → keys (`uv run btcli`) → edit `.env` (copy from `.env.example`) → fund wallet → `uv run btcli subnet register --netuid 467 --network test …` → open `AXON_PORT` → `uv run lemma miner start`. Details: [miner.md](miner.md).

**Validator:** same env/keys as above, then **`bash scripts/prebuild_lean_image.sh`** (first build is large) → **`bash scripts/start_lean_docker_worker.sh`** → `uv run lemma doctor` → `uv run lemma validator dry-run` → `uv run lemma validator start`. Details: [validator.md](validator.md).

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and sync

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
# For development/testing instead: uv sync --extra dev --extra btcli
```

Use one Python environment and one installer: `uv`. The core `lemma` repo owns
the subnet dependencies and the `lemma` command. All commands (`doctor`, `miner`,
`validator`, `corpus`, `weights`) read the same `.env`.

Default `uv sync` installs from **PyPI** and keeps only the **`bittensor`** SDK needed by Lemma itself. Add `--extra btcli` when you want repo-local wallet/register commands: it pulls in the official **[bittensor-cli](https://pypi.org/project/bittensor-cli/)** package through **`bittensor[cli]`**. **`btcli`** is only the **command name** those packages put on your `PATH` — there is no legitimate PyPI package you should install called `btcli`; typosquat packages have existed, so always use **`bittensor`**, **`bittensor-cli`**, or **`bittensor[cli]`** from PyPI.

## Run Local Commands

```bash
uv run lemma --help
uv run btcli --help
```

Run these from the core `lemma` repo root. `uv run btcli` requires
`uv sync --extra btcli`; `uv run lemma` works after the normal sync.

## Keys (Bittensor CLI: `btcli`)

Keys live under `~/.bittensor/wallets/`. Commands below use the **`btcli`** executable from **`bittensor-cli`** (see above).

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
uv run btcli wallet balance --wallet.name my_wallet
```

Registration and stake: [Bittensor CLI](https://docs.learnbittensor.org/).

## Configure `.env`

Copy `.env.example` to `.env` and edit. Required fields:

```
SUBTENSOR_NETWORK=test
SUBTENSOR_CHAIN_ENDPOINT=wss://test.finney.opentensor.ai:443
NETUID=467
BT_WALLET_COLD=my_wallet
BT_WALLET_HOT=miner   # or your validator hotkey
AXON_PORT=8091        # miners only
LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker  # validators only
```

See `.env.example` for the full set with defaults.

## Register on-chain

Use the same network/netuid with `uv run btcli` as in `.env`: **Lemma (Subnet 467)** on **testnet** (`SUBTENSOR_NETWORK=test`), not Finney (mainnet).

```bash
uv run btcli subnet show --netuid 467 --network test
uv run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey miner
```

## Miner

```bash
uv run lemma miner start
```

Open inbound `AXON_PORT`. Set `AXON_EXTERNAL_IP` explicitly for production miners, or opt into HTTPS public-IP discovery with `AXON_DISCOVER_EXTERNAL_IP=true`.

## Validator

Build sandbox image (first build is large) and start the long-lived Lean worker:

```bash
bash scripts/prebuild_lean_image.sh
bash scripts/start_lean_docker_worker.sh
uv run lemma validator dry-run    # scoring loop without writing weights
uv run lemma validator start      # scoring loop + set_weights
```

Use **`uv run lemma validator start`** only from the repo root.

## Checklist

| Step | Command / action |
| ---- | ---------------- |
| Deps | `uv sync --extra btcli` (`--extra dev` too if developing) |
| Keys | `uv run btcli` coldkey + hotkey |
| Env | Copy `.env.example` → `.env`, edit |
| Chain | Fund + `uv run btcli subnet register` |
| Lean | `scripts/prebuild_lean_image.sh` + `scripts/start_lean_docker_worker.sh` (validators) |
| Miner | `uv run lemma miner start` |
| Validator | `uv run lemma validator start` |

[miner.md](miner.md), [validator.md](validator.md), [testing.md](testing.md).
