# Lemma

**Lemma is a [Bittensor](https://docs.learnbittensor.org/) subnet that pays miners to produce kernel-verified Lean proofs of hard, fresh theorems.**

Lemma posts theorem challenges. Miners use AI to write Lean proof files.
Validators use Lean to check them. Valid proofs become eligible for miner
rewards.

Bitcoin's miners are paid to securitize blockspace. Bittensor's miners are paid
to produce useful intelligence. Lemma's miners are paid to produce
kernel-verified proofs of theorems that did not have a known proof at the start
of the epoch.

A Lemma round is simple:

1. The subnet publishes a theorem statement.
2. Miners use AI to write candidate Lean proof scripts.
3. Validators verify those scripts with the pinned Lean toolchain.
4. Verified proofs earn a share of the epoch's budget; whatever the network does not earn burns to the subnet owner.

Theorems come from three streams — perturbed Mathlib lemmas, open Mathlib
`sorry`s, and competition-style formalizations — and must pass non-triviality
and freshness gates before publication.

Lemma is still proof-of-concept software. It currently runs on Bittensor testnet as **subnet 467** (`--network test`; set `NETUID=467` in `.env`). Mainnet, also known as Finney, is separate. Only treat mainnet rewards or tokens as relevant when the deployment you are following is registered, active, and matched to the correct **network** and **netuid**.

For the full mechanism, see [docs/litepaper-v2.md](docs/litepaper-v2.md); per-epoch budget detail is in [docs/burn.md](docs/burn.md).

## Quick start

To try the CLI locally:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
```

Use one environment and one tool: `uv`. The Lemma `.venv` holds subnet dependencies and the `lemma` command (`doctor`, `miner`, `validator`, `corpus`, `weights`). Wallets use `btcli` from [bittensor-cli](https://pypi.org/project/bittensor-cli/); install it here with `uv sync --extra btcli` (or `uv sync --extra dev --extra btcli` for development).

**Validators:** start with `lemma validator start` (or Docker `ENTRYPOINT ["lemma"]` / `CMD ["validator", "start"]`).

### Operators

The sample [`docker-compose.yml`](docker-compose.yml) runs Lemma services in containers. It also mounts **`/var/run/docker.sock`** so validators can spawn isolated proof-checking containers. That socket is high privilege. Lock down the host before using this setup in production.

In the miner docs, **axon** is Bittensor's term for the network address and port where your miner listens for validator traffic. Open that port intentionally in firewalls and cloud security groups.

## References

- [Bittensor](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0

## Original Contributors

Spaceτime, Maciej Kula, and Infinitao.
