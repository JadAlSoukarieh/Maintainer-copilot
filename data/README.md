# Data Layout

This directory holds dataset files copied from Colab and split or validation outputs used locally in VS Code.

- `raw/`: source issue dataset exports and fetch metadata copied from Colab.
- `processed/`: train/validation/test splits, exclusions, manifests, and hash files produced by data preparation scripts in Colab or later VS Code preprocessing scripts.
- `golden/`: hand-curated or reviewed evaluation sets used by later eval scripts.

Do not place model artifacts here. Large `.jsonl` files under this tree are tracked with Git LFS.

