"""Download the pretrained HyenaDNA encoder into the shared models folder."""
from huggingface_hub import snapshot_download

path = snapshot_download(
    "LongSafari/hyenadna-small-32k-seqlen-hf",
    local_dir="/app/data/models/hyenadna-32k",
)
print("saved to", path)