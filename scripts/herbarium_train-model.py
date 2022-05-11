import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

import fire
import flash
import pandas as pd
import torch
from flash.core.data.io.input_transform import InputTransform
from flash.image import ImageClassificationData, ImageClassifier
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint, StochasticWeightAveraging
from pytorch_lightning.loggers import WandbLogger
from timm.loss import LabelSmoothingCrossEntropy
from torchmetrics import F1Score
from torchvision import transforms as T


@dataclass
class ImageClassificationInputTransform(InputTransform):

    image_size: Tuple[int, int] = (224, 224)
    color_mean: Tuple[float, float, float] = (0.781, 0.759, 0.710)
    color_std: Tuple[float, float, float] = (0.241, 0.245, 0.249)

    def input_per_sample_transform(self):
        return T.Compose(
            [
                T.ToTensor(),
                T.Resize(self.image_size),
                T.Normalize(self.color_mean, self.color_std),
            ]
        )

    def train_input_per_sample_transform(self):
        return T.Compose(
            [
                T.TrivialAugmentWide(),
                T.RandomPosterize(bits=2),
                T.ToTensor(),
                T.Resize(self.image_size),
                T.RandomHorizontalFlip(),
                # T.RandomEqualize(),
                # T.ColorJitter(brightness=0.2, hue=0.1),
                T.RandomAutocontrast(),
                T.RandomAdjustSharpness(sharpness_factor=2),
                T.GaussianBlur(kernel_size=(5, 9), sigma=(0.1, 5)),
                T.RandomAffine(degrees=10, scale=(0.9, 1.1), translate=(0.1, 0.1)),
                # T.RandomPerspective(distortion_scale=0.1),
                T.Normalize(self.color_mean, self.color_std),
            ]
        )

    def target_per_sample_transform(self) -> Callable:
        return torch.as_tensor


def load_df_train(dataset_dir: str) -> pd.DataFrame:
    with open(os.path.join(dataset_dir, "train_metadata.json")) as fp:
        train_data = json.load(fp)
    train_annotations = pd.DataFrame(train_data["annotations"])
    train_images = pd.DataFrame(train_data["images"]).set_index("image_id")
    train_categories = pd.DataFrame(train_data["categories"]).set_index("category_id")
    train_institutions = pd.DataFrame(train_data["institutions"]).set_index("institution_id")
    df_train = pd.merge(train_annotations, train_images, how="left", right_index=True, left_on="image_id")
    df_train = pd.merge(df_train, train_categories, how="left", right_index=True, left_on="category_id")
    df_train = pd.merge(df_train, train_institutions, how="left", right_index=True, left_on="institution_id")
    return df_train


def inference(trainer, model, df_test: pd.DataFrame, dataset_dir: str) -> pd.DataFrame:
    print(f"inference for {len(df_test)} images")
    print(df_test.head())

    datamodule = ImageClassificationData.from_data_frame(
        input_field="file_name",
        # target_fields="category_id",
        predict_data_frame=df_test,
        # for simplicity take just fraction of the data
        # predict_data_frame=test_images[:len(test_images) // 100],
        predict_images_root=os.path.join(dataset_dir, "test_images"),
        predict_transform=ImageClassificationInputTransform,
        batch_size=16,
        transform_kwargs={"image_size": (384, 384)},
        num_workers=6,
    )

    predictions = []
    for lbs in trainer.predict(model, datamodule=datamodule, output="labels"):
        # lbs = [torch.argmax(p["preds"].float()).item() for p in preds]
        predictions += lbs

    submission = pd.DataFrame({"Id": df_test.index, "Predicted": predictions}).set_index("Id")
    return submission


def main(
    dataset_dir: str = "/home/jirka/Datasets/herbarium-2022-fgvc9",
    checkpoints_dir: str = "/home/jirka/Workspace/checkpoints_herbarium-flash",
    batch_size: int = 24,
    num_workers: int = 12,
    model_backbone: str = "efficientnet_b3",
    model_pretrained: bool = False,
    optimizer: str = "AdamW",
    image_size: int = 320,
    lr_scheduler: Optional[str] = None,
    learning_rate: float = 5e-3,
    label_smoothing: float = 0.01,
    max_epochs: int = 20,
    gpus: int = 1,
    val_split: float = 0.1,
    early_stopping: Optional[float] = None,
    swa: Optional[float] = None,
    run_inference: bool = True,
    **trainer_kwargs: Dict[str, Any],
) -> None:
    print(f"Additional Trainer args: {trainer_kwargs}")
    df_train = load_df_train(dataset_dir)

    with open(os.path.join(dataset_dir, "test_metadata.json")) as fp:
        test_data = json.load(fp)
    df_test = pd.DataFrame(test_data).set_index("image_id")

    datamodule = ImageClassificationData.from_data_frame(
        input_field="file_name",
        target_fields="category_id",
        # for simplicity take just half of the data
        train_data_frame=df_train,
        # train_data_frame=df_train[:len(df_train) // 2],
        train_images_root=os.path.join(dataset_dir, "train_images"),
        train_transform=ImageClassificationInputTransform,
        val_transform=ImageClassificationInputTransform,
        transform_kwargs={"image_size": (image_size, image_size)},
        batch_size=batch_size,
        num_workers=num_workers,
        val_split=val_split,
    )

    model = ImageClassifier(
        backbone=model_backbone,
        metrics=F1Score(num_classes=datamodule.num_classes, average="macro"),
        pretrained=model_pretrained,
        loss_fn=LabelSmoothingCrossEntropy(label_smoothing),
        optimizer=optimizer,
        learning_rate=learning_rate,
        lr_scheduler=lr_scheduler,
        num_classes=datamodule.num_classes,
    )

    # Trainer Args
    logger = WandbLogger(project="Flash_tract-image-segmentation")
    log_id = str(logger.experiment.id)
    monitor = "val_f1score"
    cbs = [ModelCheckpoint(dirpath=checkpoints_dir, filename=f"{log_id}", monitor=monitor, mode="max", verbose=True)]
    if early_stopping is not None:
        cbs.append(EarlyStopping(monitor=monitor, min_delta=early_stopping, mode="max", verbose=True))
    if isinstance(swa, float):
        cbs.append(StochasticWeightAveraging(swa_epoch_start=swa))

    trainer = flash.Trainer(
        callbacks=cbs,
        max_epochs=max_epochs,
        precision="bf16" if gpus else 32,
        gpus=gpus,
        accelerator="ddp" if gpus > 1 else None,
        logger=logger,
        **trainer_kwargs,
    )

    # Train the model
    # trainer.finetune(model, datamodule=datamodule, strategy="no_freeze")
    trainer.finetune(model, datamodule=datamodule, strategy=("freeze_unfreeze", 2))

    # Save the model!
    checkpoint_name = f"herbarium-classif-{log_id}_{model_backbone}-{image_size}px.pt"
    trainer.save_checkpoint(os.path.join(checkpoints_dir, checkpoint_name))

    if run_inference:
        submission = inference(trainer, model, df_test, dataset_dir)
        submission_name = f"submission_herbarium-{log_id}_{model_backbone}-{image_size}.csv"
        submission.to_csv(os.path.join(checkpoints_dir, submission_name))


if __name__ == "__main__":
    fire.Fire(main)
