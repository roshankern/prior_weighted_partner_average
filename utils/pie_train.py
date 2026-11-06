"""Train PIE with its within-dataset recipe and predict with its best checkpoint (2.train_test/1.train_pie.ipynb,
4.training_cost.ipynb). Needs PIE's environment (ArcInstitute/pie @ 21a526a) and a GPU.

The recipe is experiment=replogle_wdataset (batch 16, learning rate 1e-4, 250 warmup steps, a validation every 100
steps) on one GPU with gradient accumulation 8, the recipe's effective batch of 128, and two changes made from outside
PIE's code, as K062-pie-eight/train_pie.py: at most 2,000 steps (the learning rate is constant until step 4,500, so a
run is the recipe's first 2,000 steps), and early stopping after 6 validations without a better AUPRC.
"""

import os
import resource
import time
from pathlib import Path

from lightning.pytorch.callbacks import Callback, EarlyStopping
from lightning.pytorch.loggers import CSVLogger

import pie.train as T
from paths import data_dir
from pie.config import compose_train_config
from pie.predict import RowSource, load_checkpoint, predict_loaded, write_predictions_parquet

STEPS = 2000
SOURCES = ["esm2", "ncbi_text", "string_space", "depmap_gene_effect", "context_text", "perturbation_text"]
_build_trainer = T.build_trainer
# PIE logs to wandb; keep the metrics as CSV in the run folder instead
T._make_logger = lambda cfg, run_dir, run_id: CSVLogger(save_dir=str(run_dir), name="csv")


def cpu_seconds():
    return sum(getattr(resource.getrusage(who), f) for who in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)
               for f in ("ru_utime", "ru_stime"))


class ValidationLog(Callback):
    """Appends step, seconds since `start` and validation AUPRC to a CSV at every validation."""

    def __init__(self, path, start):
        self.path, self.start = Path(path), start

    def on_validation_end(self, trainer, module):
        if trainer.sanity_checking:
            return
        if not self.path.exists():
            self.path.write_text("step,seconds,val_binary_auprc\n")
        with self.path.open("a") as f:
            f.write(f"{trainer.global_step},{time.perf_counter() - self.start:.3f},{trainer.callback_metrics[T.MONITOR].item()}\n")


def _env(run_dir):
    # PIE reads its roots from the environment; the run's config stores paths relative to them
    os.environ.update(PIE_RUNS_ROOT=str(run_dir.parent), PIE_CACHE_DIR=str(run_dir.parent / "cache"),
                      PIE_DATA_ROOT=str(data_dir("priors", "raw")), WANDB_ENTITY="unused", WANDB_PROJECT="unused")


def train(run_dir, preprocessed, split_dir, resume=True):
    """Train PIE on split_dir's train.json, stopping on its val.json, into run_dir (checkpoints, csv/, and
    validations.csv). Resumes from run_dir/last.ckpt when there is one and `resume`; otherwise starts over.
    Returns the wall and CPU seconds (this process and its children) of this call."""
    run_dir = Path(run_dir)
    start, cpu = time.perf_counter(), cpu_seconds()
    resume = resume and (run_dir / "last.ckpt").is_file() and (run_dir / "data_stats.json").is_file()
    if not resume:
        (run_dir / "validations.csv").unlink(missing_ok=True)

    def build_trainer(cfg, rd, logger):
        trainer = _build_trainer(cfg, rd, logger)
        trainer.callbacks.extend([EarlyStopping(monitor=T.MONITOR, mode="max", patience=6, check_on_train_epoch_end=False),
                                  ValidationLog(run_dir / "validations.csv", start)])
        return trainer

    T.build_trainer = build_trainer
    _env(run_dir)
    T.run_train(compose_train_config([
        "experiment=replogle_wdataset", f"experiment_name={run_dir.name}", "resume=true" if resume else "overwrite=true",
        f"data.preprocessed_dirs=[{preprocessed}]", f"data.split_dir={split_dir}",
        *(f"data.source_dirs.{s}={data_dir('priors', 'raw', s)}" for s in SOURCES),
        f"data.gene_text_dir={data_dir('priors', 'raw', 'gene_text')}",
        "trainer.devices=1", "trainer.accumulate_grad_batches=8", f"trainer.max_steps={STEPS}",
        "trainer.val_every_n_steps=100", "trainer.log_every_n_steps=50",
        f"scheduler.warmup_fraction={250 / STEPS}",  # keeps the recipe's 250 warmup steps
        "logger.enabled=true", "logger.group=null", "logger.tags=[]",
    ]))
    return time.perf_counter() - start, cpu_seconds() - cpu


def predict(run_dir, rows_json, path):
    """Predict the rows of a split file with run_dir's best checkpoint, with the run's training knockdowns as
    evidence, into a parquet in PIE's prediction format."""
    run_dir = Path(run_dir)
    _env(run_dir)
    preds = predict_loaded(load_checkpoint(run_dir / "best_auprc.ckpt"), RowSource("split", Path(rows_json)), None, "cuda")
    write_predictions_parquet(preds, Path(path))
