# Classifier Artifact Layout

This directory is the landing zone for classifier-related outputs copied from Colab and for later comparison reports generated in VS Code.

- `classical/`: classical baseline artifacts such as `model.joblib`, metrics, and predictions.
- `transformer/`: Hugging Face-style transformer model export, metrics, model card, and predictions.
- `llm_baseline/`: prompt-based baseline predictions, metrics, and cost summary when available.
- `comparison/`: cross-model comparison reports and summary material.
- `artifact_manifest.template.json`: template describing the expected artifact inventory and where each file comes from.

Do not commit large artifacts before Git LFS is installed and tracking is active.

