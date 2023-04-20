from typing import Optional

import torch
import torch.nn.functional as F
from attr import define

from lizrd.datasets import wikibookdata


@define
class ConditionalTrainer:
    model: torch.nn.Module
    optimizer: torch.optim.Optimizer
    train_dataloader: wikibookdata.ProcessedDatasetWrapper
    batch_size: int
    vocab_size: int
    mask_percent: float
    mixed_precision: bool = False
    scaler: Optional[torch.cuda.amp.GradScaler] = None

    def __attrs_post_init__(self):
        self.scaler = torch.cuda.amp.GradScaler(enabled=self.mixed_precision)

    def optimize(self, loss):
        self.optimizer.zero_grad()
        self.scaler.scale(loss).backward()
        self.scaler.step(self.optimizer)
        self.scaler.update()

    def _train_step(
        self,
        step,
    ):
        self.model.train()
        processed_batch = self.train_dataloader.get_batch()
        assert isinstance(processed_batch, wikibookdata.ProcessedBatch)
        x_set = processed_batch.masked_tokens
        y_token_set = processed_batch.tokens
        y_mask_set = processed_batch.mask_mask

        loss = self.calculate_loss(x_set, y_token_set, y_mask_set)
        self.optimize(loss)

    def train(self, n_steps: int):
        for step in range(n_steps):
            self._train_step(step)
            if step % 500 == 0:
                print(f"Step {step}")

    def calculate_loss(self, x_set, y_token_set, y_mask_set):
        if self.mixed_precision:
            with torch.autocast(
                device_type="cuda", enabled=self.mixed_precision, dtype=torch.float16
            ):
                model_output = self.model(x_set)
        else:
            model_output = self.model(x_set)

        mask_loss = F.cross_entropy(
            model_output.reshape(-1, self.vocab_size),
            y_token_set.reshape(-1).long(),
            reduction="none",
        )
        mask_loss *= y_mask_set.reshape(-1)
        loss = mask_loss.mean() / self.mask_percent
        return loss
