"""
finetune_mursit.py — Mursit-Base-TR Contrastive Fine-Tuning Grid
================================================================

contrastive_triplets_train.jsonl ve contrastive_triplets_val.jsonl kullanarak
Mursit-Base-TR-Retrieval modelini native PyTorch contrastive loss ile eğitir.

Stratejiler:
  1. v1_full   : Full Fine-Tuning (lr=2e-5, 3 epoch)
  2. v2_frozen : Katman Dondurma - İlk 6 katman dondurulur (lr=3e-5, 3 epoch)
  3. v3_lowlr  : Düşük LR Full Fine-Tuning (lr=1e-5, 4 epoch)

KULLANIM:
    cd BACKEND
    python src/finetune_mursit.py
    python src/finetune_mursit.py --batch-size 16
    python src/finetune_mursit.py --only v1_full
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path

# ─── Windows OpenMP Crash Önleme (0xC0000005 / exit code 3221225477) ──────────
# OMP ve MKL ortam değişkenleri torch import'undan ÖNCE ayarlanmalı.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import torch
import torch.nn.functional as F

# torch import sonrası da ayarla (bazı versiyonlarda gerekli)
torch.set_num_threads(1)

# ─── Path ─────────────────────────────────────────────────────────────────────
_SRC_DIR     = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
for _p in [Path(_BACKEND_DIR) / ".env", Path(_BACKEND_DIR).parent / ".env"]:
    if _p.exists():
        load_dotenv(dotenv_path=_p)
        break

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("LawAgent.FineTune")

# ─── Sabitler ─────────────────────────────────────────────────────────────────
BASE_MODEL            = "newmindai/Mursit-Base-TR-Retrieval"
TRAIN_TRIPLETS        = os.path.join(_BACKEND_DIR, "eval", "contrastive_triplets_train.jsonl")
VAL_TRIPLETS          = os.path.join(_BACKEND_DIR, "eval", "contrastive_triplets_val.jsonl")
OUTPUT_BASE           = os.path.join(_SRC_DIR, "data")
SEED                  = 42
EARLY_STOP_PATIENCE   = 2  # Val loss ardı ardına bu kadar epoch iyileşmezse dur

# Grid Stratejileri
GRID_STRATEGIES = [
    {
        "tag": "v1_full",
        "lr": 2e-5,
        "epochs": 3,
        "freeze_lower": False,
        "desc": "Full Fine-Tuning (lr=2e-5, 3ep)",
    },
    {
        "tag": "v2_frozen",
        "lr": 3e-5,
        "epochs": 3,
        "freeze_lower": True,
        "desc": "Katman Dondurma - İlk 6 katman donduruldu (lr=3e-5, 3ep)",
    },
    {
        "tag": "v3_lowlr",
        "lr": 1e-5,
        "epochs": 4,
        "freeze_lower": False,
        "desc": "Muhafazakar Low-LR (lr=1e-5, 4ep)",
    },
]


def load_triplets(path: str) -> list[tuple[str, str, str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Triplet dosyası bulunamadı: {path}")

    triplets = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            a = obj.get("anchor", "")
            p = obj.get("positive", "")
            n = obj.get("negative", "")
            if a and p and n:
                triplets.append((a, p, n))

    log.info(f"Triplet yüklendi: {len(triplets)} <- {os.path.basename(path)}")
    return triplets


def compute_batch_loss(model, batch: list[tuple[str, str, str]], device: str, temp: float = 0.05) -> torch.Tensor:
    """
    In-batch contrastive MultipleNegativesRankingLoss hesaplar.
    """
    tok = model.tokenizer
    anchors   = [b[0] for b in batch]
    positives = [b[1] for b in batch]
    negatives = [b[2] for b in batch]

    feat_a = tok(anchors,   padding=True, truncation=True, max_length=512, return_tensors="pt")
    feat_p = tok(positives, padding=True, truncation=True, max_length=512, return_tensors="pt")
    feat_n = tok(negatives, padding=True, truncation=True, max_length=512, return_tensors="pt")

    feat_a = {k: v.to(device) for k, v in feat_a.items()}
    feat_p = {k: v.to(device) for k, v in feat_p.items()}
    feat_n = {k: v.to(device) for k, v in feat_n.items()}

    emb_a = F.normalize(model(feat_a)["sentence_embedding"], p=2, dim=1)
    emb_p = F.normalize(model(feat_p)["sentence_embedding"], p=2, dim=1)
    emb_n = F.normalize(model(feat_n)["sentence_embedding"], p=2, dim=1)

    batch_sz = len(batch)
    sim_ap = torch.matmul(emb_a, emb_p.T) / temp                  # (B, B)
    sim_an = (emb_a * emb_n).sum(dim=1, keepdim=True) / temp     # (B, 1)

    logits = torch.cat([sim_ap, sim_an], dim=1)                  # (B, B+1)
    labels = torch.arange(batch_sz, device=device, dtype=torch.long)

    return F.cross_entropy(logits, labels)


def evaluate_val_loss(model, val_triplets: list[tuple[str, str, str]], device: str, batch_size: int = 16) -> float:
    """
    Validation seti üzerinde ortalama loss hesaplar.
    """
    model.eval()
    val_loss = 0.0
    n_batches = math.ceil(len(val_triplets) / batch_size)

    with torch.no_grad():
        for i in range(0, len(val_triplets), batch_size):
            batch = val_triplets[i : i + batch_size]
            loss = compute_batch_loss(model, batch, device)
            val_loss += loss.item()

    return val_loss / max(n_batches, 1)


def freeze_transformer_layers(model, num_layers_to_freeze: int = 6) -> None:
    """
    Transformer modelinin embedding katmanını ve ilk `num_layers_to_freeze` katmanını dondurur.
    """
    try:
        auto_model = model._first_module().auto_model
        # Embeddings dondur
        if hasattr(auto_model, "embeddings"):
            for p in auto_model.embeddings.parameters():
                p.requires_grad = False
        # Katmanları dondur
        if hasattr(auto_model, "encoder") and hasattr(auto_model.encoder, "layer"):
            layers = auto_model.encoder.layer
            for i in range(min(num_layers_to_freeze, len(layers))):
                for p in layers[i].parameters():
                    p.requires_grad = False
        log.info(f"[Freeze] İlk {num_layers_to_freeze} transformer katmanı donduruldu.")
    except Exception as e:
        log.warning(f"[Freeze] Katman dondurma uygulanamadı: {e}")


def train_strategy(
    train_triplets: list[tuple[str, str, str]],
    val_triplets: list[tuple[str, str, str]],
    cfg: dict,
    batch_size: int,
    out_dir: str,
) -> dict:
    from sentence_transformers import SentenceTransformer

    tag          = cfg["tag"]
    lr           = cfg["lr"]
    epochs       = cfg["epochs"]
    freeze_lower = cfg["freeze_lower"]
    desc         = cfg["desc"]

    log.info(f"\n{'='*60}")
    log.info(f"Strateji [{tag}]: {desc}")
    log.info(f"Çıktı: {out_dir}")
    log.info(f"{'='*60}")

    if torch.cuda.is_available():
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    log.info(f"Cihaz: {device}")

    log.info(f"Base model yükleniyor: {BASE_MODEL}")
    model = SentenceTransformer(BASE_MODEL, device=device)

    # Katman dondurma kontrolü
    if freeze_lower:
        freeze_transformer_layers(model, num_layers_to_freeze=6)

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params     = sum(p.numel() for p in model.parameters())
    log.info(f"Eğitilebilir parametreler: {trainable_params:,} / {total_params:,} (%{trainable_params/total_params*100:.1f})")

    # Optimizer (sadece requires_grad=True olanlar)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad], lr=lr
    )

    n_train_batches = math.ceil(len(train_triplets) / batch_size)
    best_val_loss = float("inf")
    history = []
    patience_counter = 0
    stopped_early = False

    random.seed(SEED)
    shuffled_train = list(train_triplets)

    t0 = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        random.shuffle(shuffled_train)
        running_train_loss = 0.0

        for b_idx in range(0, len(shuffled_train), batch_size):
            batch = shuffled_train[b_idx : b_idx + batch_size]

            optimizer.zero_grad()
            loss = compute_batch_loss(model, batch, device)
            loss.backward()
            optimizer.step()

            running_train_loss += loss.item()

        avg_train_loss = running_train_loss / max(n_train_batches, 1)
        avg_val_loss   = evaluate_val_loss(model, val_triplets, device, batch_size)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            model.save(out_dir)
            log.info(
                f"Epoch {epoch}/{epochs} — Train Loss: {avg_train_loss:.4f} "
                f"| Val Loss: {avg_val_loss:.4f}  ✓ Yeni en iyi checkpoint kaydedildi."
            )
        else:
            patience_counter += 1
            log.info(
                f"Epoch {epoch}/{epochs} — Train Loss: {avg_train_loss:.4f} "
                f"| Val Loss: {avg_val_loss:.4f}  [patience {patience_counter}/{EARLY_STOP_PATIENCE}]"
            )

        history.append({
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "val_loss": round(avg_val_loss, 4),
            "early_stopped": False,  # sonradan güncellenecek
        })

        if patience_counter >= EARLY_STOP_PATIENCE:
            log.info(
                f"[Early Stop] Strateji [{tag}]: Epoch {epoch}'de durduruldu "
                f"({EARLY_STOP_PATIENCE} epoch boyunca val loss iyileşmedi). "
                f"En iyi val loss: {best_val_loss:.4f}"
            )
            history[-1]["early_stopped"] = True
            stopped_early = True
            break

    elapsed = time.time() - t0
    log.info(f"Strateji [{tag}] tamamlandı: {elapsed:.1f}s | En İyi Val Loss: {best_val_loss:.4f} | Early Stop: {stopped_early}")

    return {
        "tag": tag,
        "desc": desc,
        "best_val_loss": round(best_val_loss, 4),
        "history": history,
        "out_dir": out_dir,
        "elapsed_sec": round(elapsed, 1),
        "stopped_early": stopped_early,
        "stopped_at_epoch": history[-1]["epoch"] if history else 0,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Mursit-Base-TR Contrastive Fine-Tuning Strategy Sweep")
    parser.add_argument("--only", choices=["v1_full", "v2_frozen", "v3_lowlr"], default=None)
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    train_triplets = load_triplets(TRAIN_TRIPLETS)
    val_triplets   = load_triplets(VAL_TRIPLETS)

    results = []

    for cfg in GRID_STRATEGIES:
        tag = cfg["tag"]
        if args.only and args.only != tag:
            continue

        out_dir = os.path.join(OUTPUT_BASE, f"fine_tuned_mursit_{tag}")
        os.makedirs(out_dir, exist_ok=True)

        res = train_strategy(
            train_triplets=train_triplets,
            val_triplets=val_triplets,
            cfg=cfg,
            batch_size=args.batch_size,
            out_dir=out_dir,
        )
        results.append(res)

        # Config dosyası yaz
        cfg_path = os.path.join(out_dir, "finetune_config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({
                "base_model": BASE_MODEL,
                "strategy": cfg,
                "best_val_loss": res["best_val_loss"],
                "history": res["history"],
                "n_train_triplets": len(train_triplets),
                "n_val_triplets": len(val_triplets),
                "early_stop_patience": EARLY_STOP_PATIENCE,
                "stopped_early": res["stopped_early"],
                "stopped_at_epoch": res["stopped_at_epoch"],
                "diversity_penalty": "KAPALI",
                "note": "Diversity Penalty bu deneyde kapalı tutuldu, izole test bir sonraki adımda yapılacak",
            }, f, ensure_ascii=False, indent=2)

    # Kazanan stratejiyi belirle (En düşük val_loss)
    if results:
        winner = min(results, key=lambda x: x["best_val_loss"])
        print("\n" + "=" * 60)
        print("FİNE-TUNING STRATEJİ SWEEP SONUÇLARI")
        print("=" * 60)
        for r in results:
            w_flag = " 🏆 [KAZANAN]" if r["tag"] == winner["tag"] else ""
            print(f"  {r['tag']:<12} ({r['desc']}) -> Best Val Loss: {r['best_val_loss']:.4f}{w_flag}")
        print("=" * 60 + "\n")

        # Kazananı fine_tuned_mursit/ klasörüne kopyala
        final_dir = os.path.join(OUTPUT_BASE, "fine_tuned_mursit")
        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)
        shutil.copytree(winner["out_dir"], final_dir)
        print(f"[OK] Kazanan model (`{winner['tag']}`) kaydedildi -> {final_dir}")


if __name__ == "__main__":
    main()
