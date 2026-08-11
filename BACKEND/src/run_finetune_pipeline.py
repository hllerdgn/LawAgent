"""
run_finetune_pipeline.py — Contrastive Fine-Tuning Tam Otomasyon Pipeline'ı
=============================================================================

1. prepare_triplets.py   (Train/Val split & Leakage check ile 1.113 triplet hazırlar)
2. finetune_mursit.py     (v1_full, v2_frozen, v3_lowlr grid sweep)
3. eval_v2.py             (Baseline ve her strategy checkpoint'i eval eder)
4. Winner Selection       (En iyi held-out Hit@1 ve MRR sunan modeli seçer)
5. compare_finetune.py    (finetune_eval_report.md & CSV çıktılarını üretir)
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import subprocess
import time

_SRC_DIR     = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SRC_DIR)

PYTHON_EXE = sys.executable

# Windows OpenMP crash önleme: alt süreçlere geçirilecek ortam değişkenleri
# (bu değişkenler torch importtan önce subprocess ortamında mevcut olmalı)
_WIN_ENV = os.environ.copy()
_WIN_ENV.update({
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
})

def run_step(cmd: list[str], desc: str) -> None:
    print(f"\n{'='*70}")
    print(f" ADIM: {desc}")
    print(f" KOMUT: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=_BACKEND_DIR, env=_WIN_ENV)
    if res.returncode != 0:
        print(f"HATA: {desc} başarısız oldu (exit code {res.returncode})")
        sys.exit(res.returncode)
    print(f"-> [OK] {desc} tamamlandı ({time.time()-t0:.1f}s)\n")

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # 1. Triplet Hazırlığı (85% Train / 15% Val + Leakage Check)
    run_step(
        [PYTHON_EXE, "src/prepare_triplets.py"],
        "1/5 Triplet Hazırlığı & Sızıntı Denetimi (Train/Val Split)"
    )

    # 2. Fine-Tuning Sweep (v1_full, v2_frozen, v3_lowlr)
    run_step(
        [PYTHON_EXE, "src/finetune_mursit.py", "--batch-size", "16"],
        "2/5 Fine-Tuning Grid Sweep (Full, Katman Dondurma, Low-LR)"
    )

    # 3. Baseline Eval (Mevcut Mursit-Base-TR) eğer daha önce yapılmadıysa
    baseline_dir = os.path.join(_BACKEND_DIR, "eval", "results_v2")
    if not os.path.exists(os.path.join(baseline_dir, "raw_results_heldout.csv")):
        run_step(
            [PYTHON_EXE, "src/eval_v2.py", "--out-dir", "eval/results_v2", "--no-determinism"],
            "3a/5 Baseline Model Eval (Mursit-Base-TR)"
        )

    # 4. Strategy Checkpoint Eval (v1_full, v2_frozen, v3_lowlr)
    strategies = ["v1_full", "v2_frozen", "v3_lowlr"]
    eval_results = {}

    for strat in strategies:
        model_dir = os.path.join(_BACKEND_DIR, "src", "data", f"fine_tuned_mursit_{strat}")
        if not os.path.exists(model_dir):
            continue

        out_eval_dir = f"eval/results_finetune_{strat}"
        run_step(
            [
                PYTHON_EXE, "src/eval_v2.py",
                "--out-dir", out_eval_dir,
                "--model-path", f"src/data/fine_tuned_mursit_{strat}",
                "--collection-name", f"lawagent_mursit_ft_{strat}",
                "--no-determinism"
            ],
            f"3b/5 Eval Strategy Checkpoint [{strat}]"
        )

        fail_path = os.path.join(_BACKEND_DIR, out_eval_dir, "failure_analysis.json")
        hit1, mrr = 0.0, 0.0
        if os.path.exists(fail_path):
            with open(fail_path, encoding="utf-8") as f:
                h_meta = json.load(f).get("heldout_analysis", {})
                hit1 = h_meta.get("success_rate_hit1", 0.0)
                mrr  = h_meta.get("mrr", 0.0)

        eval_results[strat] = {"hit1": hit1, "mrr": mrr, "eval_dir": out_eval_dir, "model_dir": model_dir}

    # 5. En İyi Model Seçimi
    if not eval_results:
        print("HATA: Hiçbir strategy checkpoint değerlendirilemedi!")
        sys.exit(1)

    winner_strat = max(eval_results.keys(), key=lambda s: (eval_results[s]["hit1"], eval_results[s]["mrr"]))
    winner = eval_results[winner_strat]

    print("\n" + "="*70)
    print(f" 🏆 KAZANAN MODEL SEÇİLDİ: [{winner_strat}]")
    print(f"    Held-Out Hit@1: {winner['hit1']:.4f} | MRR: {winner['mrr']:.4f}")
    print("="*70 + "\n")

    final_model_dir = os.path.join(_BACKEND_DIR, "src", "data", "fine_tuned_mursit")
    final_eval_dir  = os.path.join(_BACKEND_DIR, "eval", "results_finetune")

    if os.path.exists(final_model_dir):
        shutil.rmtree(final_model_dir)
    shutil.copytree(winner["model_dir"], final_model_dir)

    if os.path.exists(final_eval_dir):
        shutil.rmtree(final_eval_dir)
    shutil.copytree(winner["eval_dir"], final_eval_dir)

    # 6. Rapor Üretimi
    run_step(
        [PYTHON_EXE, "src/compare_finetune.py"],
        "5/5 Karşılaştırma Raporu Üretimi (finetune_eval_report.md & CSV'ler)"
    )

    print("\n" + "="*70)
    print(" FİNE-TUNING & EVALUATION PIPELINE BAŞARIYLA TAMAMLANDI!")
    print(f" Rapor  : eval/finetune_eval_report.md")
    print(f" Gold CSV: eval/raw_results_finetuned_gold.csv")
    print(f" Held CSV: eval/raw_results_finetuned_heldout.csv")
    print(f" Model  : src/data/fine_tuned_mursit/ (Strateji: {winner_strat})")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
