# Lemma

**Lemma is a [Bittensor](https://docs.learnbittensor.org/) subnet for using AI to prove mathematical theorems.**

Lemma posts theorem challenges. Miners use AI to write Lean proof files.
Validators use Lean to check them. Valid proofs become eligible for miner
rewards.

Bitcoin rewards miners for securing the network. Bittensor rewards miners for
producing useful intelligence. Lemma rewards miners for producing correct
proofs.

A Lemma round is simple:

1. The subnet publishes a theorem statement.
2. Miners use AI to write candidate Lean proof scripts.
3. Validators verify those scripts with the pinned Lean toolchain.
4. Passing proofs become eligible for miner rewards under Lemma's subnet rules; failing proofs do not.

Anything that can be formalized as a Lean statement can become work for Lemma:
algebra, number theory, logic, combinatorics, geometry, computer science,
cryptography, and more.

For the per-epoch budget mechanism, see [docs/burn.md](docs/burn.md).

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
```

CLI: `lemma doctor`, `lemma miner start`, `lemma validator start`,
`lemma validator dry-run`, `lemma corpus push <s3-url>`, `lemma weights`.

### Operators

The sample [`docker-compose.yml`](docker-compose.yml) runs Lemma services in
containers and mounts `/var/run/docker.sock` so validators can spawn isolated
proof-checking containers. Lock down the host before using this setup.

## References

- [Bittensor](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
