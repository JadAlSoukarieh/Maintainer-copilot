# Transformer Model Export

Expected files in this directory:

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`
- `special_tokens_map.json`
- `vocab.json`
- `merges.txt`

This directory should mirror the saved transformer model export from Colab.

- Produced by: Colab
- Consumed by: later model-server loading work and local artifact verification

Do not rename files unless the training/export pipeline changes as well.

