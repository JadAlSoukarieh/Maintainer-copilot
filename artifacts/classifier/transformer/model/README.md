# Transformer Model Export

Required files in this directory:

- `config.json`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`

Optional files in this directory:

- `special_tokens_map.json`
- `vocab.json`
- `merges.txt`
- `training_args.bin`

This directory should mirror the full Hugging Face `save_pretrained` export copied from Colab. The model and tokenizer files must stay together because later loading code will rely on the export as a complete package rather than piecing individual files together by hand.

- Produced by: Colab
- Consumed by: later model-server loading work and local artifact verification

`training_args.bin` may appear as an extra Hugging Face Trainer artifact. It is optional and does not replace `training_args.json`.

Do not rename files unless the training/export pipeline changes as well.
