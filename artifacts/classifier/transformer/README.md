# Transformer Classifier Artifacts

Expected files in this directory:

- `model/`
- `metrics.json`
- `confusion_matrix.json`
- `test_predictions.jsonl`
- `model_card.md`
- `training_args.json`

These outputs come from the transformer training run in Colab. The nested `model/` directory should contain the saved tokenizer and model files needed for later serving work, but model loading is not implemented in this repo yet.

- Produced by: Colab
- Consumed by: artifact verification, comparison scripts, and later model-server integration

