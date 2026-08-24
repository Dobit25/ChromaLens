"""SCHP Augment-CE2P inference graph with portable activated BatchNorm.

The architecture is adapted from Self-Correction for Human Parsing at pinned
upstream commit ``eb84c432cc697f494d99662a05f2335eb2f26095``. The upstream
source is MIT licensed by Peike Li. ChromaLens replaces the historical custom
CUDA/C++ InPlaceABNSync extension with numerically equivalent PyTorch
BatchNorm-plus-activation operations for single-device inference. Module names
and state tensors remain unchanged so the ATR checkpoint can be loaded with
``strict=True``.

This module is imported lazily by :mod:`chromalens.segmentation.schp_backend`;
normal CLI help and the MediaPipe fallback do not import PyTorch.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch
from torch import Tensor, nn
from torch.nn import functional as functional


class ActivatedBatchNorm2d(nn.BatchNorm2d):
    """Portable inference-compatible replacement for upstream InPlaceABNSync."""

    def __init__(
        self,
        num_features: int,
        eps: float = 1e-5,
        momentum: float = 0.1,
        affine: bool = True,
        activation: str = "leaky_relu",
        slope: float = 0.01,
    ) -> None:
        super().__init__(
            num_features,
            eps=eps,
            momentum=momentum,
            affine=affine,
        )
        self.activation = activation
        self.slope = slope

    def forward(self, tensor: Tensor) -> Tensor:
        normalized = super().forward(tensor)
        if self.activation == "relu":
            return functional.relu(normalized, inplace=False)
        if self.activation == "leaky_relu":
            return functional.leaky_relu(
                normalized,
                negative_slope=self.slope,
                inplace=False,
            )
        if self.activation == "elu":
            return functional.elu(normalized, inplace=False)
        if self.activation == "none":
            return normalized
        raise ValueError(f"unsupported activated BatchNorm mode: {self.activation}")


def _batch_norm(num_features: int, *, affine: bool = True) -> ActivatedBatchNorm2d:
    return ActivatedBatchNorm2d(num_features, affine=affine, activation="none")


def _conv3x3(
    in_planes: int,
    out_planes: int,
    *,
    stride: int = 1,
) -> nn.Conv2d:
    return nn.Conv2d(
        in_planes,
        out_planes,
        kernel_size=3,
        stride=stride,
        padding=1,
        bias=False,
    )


class _Bottleneck(nn.Module):
    expansion = 4

    def __init__(
        self,
        inplanes: int,
        planes: int,
        *,
        stride: int = 1,
        dilation: int = 1,
        downsample: nn.Module | None = None,
        multi_grid: int = 1,
    ) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = _batch_norm(planes)
        self.conv2 = nn.Conv2d(
            planes,
            planes,
            kernel_size=3,
            stride=stride,
            padding=dilation * multi_grid,
            dilation=dilation * multi_grid,
            bias=False,
        )
        self.bn2 = _batch_norm(planes)
        self.conv3 = nn.Conv2d(planes, planes * 4, kernel_size=1, bias=False)
        self.bn3 = _batch_norm(planes * 4)
        self.relu = nn.ReLU(inplace=False)
        self.relu_inplace = nn.ReLU(inplace=True)
        self.downsample = downsample

    def forward(self, tensor: Tensor) -> Tensor:
        residual = tensor
        output = self.relu(self.bn1(self.conv1(tensor)))
        output = self.relu(self.bn2(self.conv2(output)))
        output = self.bn3(self.conv3(output))
        if self.downsample is not None:
            residual = self.downsample(tensor)
        return self.relu_inplace(output + residual)


class _PSPModule(nn.Module):
    def __init__(
        self,
        features: int,
        out_features: int = 512,
        sizes: Sequence[int] = (1, 2, 3, 6),
    ) -> None:
        super().__init__()
        self.stages = nn.ModuleList(
            [self._make_stage(features, out_features, size) for size in sizes]
        )
        self.bottleneck = nn.Sequential(
            nn.Conv2d(
                features + len(sizes) * out_features,
                out_features,
                kernel_size=3,
                padding=1,
                bias=False,
            ),
            ActivatedBatchNorm2d(out_features),
        )

    @staticmethod
    def _make_stage(features: int, out_features: int, size: int) -> nn.Sequential:
        return nn.Sequential(
            nn.AdaptiveAvgPool2d(output_size=(size, size)),
            nn.Conv2d(features, out_features, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(out_features),
        )

    def forward(self, features: Tensor) -> Tensor:
        height, width = features.shape[2:]
        priors = [
            functional.interpolate(
                stage(features),
                size=(height, width),
                mode="bilinear",
                align_corners=True,
            )
            for stage in self.stages
        ]
        priors.append(features)
        return self.bottleneck(torch.cat(priors, dim=1))


class _EdgeModule(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(256, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(512, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(1024, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
        )
        self.conv4 = nn.Conv2d(256, 2, kernel_size=3, padding=1, bias=True)
        self.conv5 = nn.Conv2d(6, 2, kernel_size=1, bias=True)

    def forward(
        self,
        first: Tensor,
        second: Tensor,
        third: Tensor,
    ) -> tuple[Tensor, Tensor]:
        height, width = first.shape[2:]
        first_features = self.conv1(first)
        second_features = self.conv2(second)
        third_features = self.conv3(third)
        first_edge = self.conv4(first_features)
        second_edge = self.conv4(second_features)
        third_edge = self.conv4(third_features)
        second_features = functional.interpolate(
            second_features,
            size=(height, width),
            mode="bilinear",
            align_corners=True,
        )
        third_features = functional.interpolate(
            third_features,
            size=(height, width),
            mode="bilinear",
            align_corners=True,
        )
        second_edge = functional.interpolate(
            second_edge,
            size=(height, width),
            mode="bilinear",
            align_corners=True,
        )
        third_edge = functional.interpolate(
            third_edge,
            size=(height, width),
            mode="bilinear",
            align_corners=True,
        )
        edge = self.conv5(torch.cat([first_edge, second_edge, third_edge], dim=1))
        edge_features = torch.cat(
            [first_features, second_features, third_features],
            dim=1,
        )
        return edge, edge_features


class _DecoderModule(nn.Module):
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(512, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(256, 48, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(48),
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(304, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
            nn.Conv2d(256, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
        )
        self.conv4 = nn.Conv2d(256, num_classes, kernel_size=1, bias=True)

    def forward(self, top: Tensor, low: Tensor) -> tuple[Tensor, Tensor]:
        height, width = low.shape[2:]
        top = functional.interpolate(
            self.conv1(top),
            size=(height, width),
            mode="bilinear",
            align_corners=True,
        )
        decoded = self.conv3(torch.cat([top, self.conv2(low)], dim=1))
        return self.conv4(decoded), decoded


class SCHPResNet101(nn.Module):
    """ATR inference graph that returns final 18-class fusion logits."""

    def __init__(self, num_classes: int = 18) -> None:
        super().__init__()
        self.inplanes = 128
        self.conv1 = _conv3x3(3, 64, stride=2)
        self.bn1 = _batch_norm(64)
        self.relu1 = nn.ReLU(inplace=False)
        self.conv2 = _conv3x3(64, 64)
        self.bn2 = _batch_norm(64)
        self.relu2 = nn.ReLU(inplace=False)
        self.conv3 = _conv3x3(64, 128)
        self.bn3 = _batch_norm(128)
        self.relu3 = nn.ReLU(inplace=False)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(64, 3)
        self.layer2 = self._make_layer(128, 4, stride=2)
        self.layer3 = self._make_layer(256, 23, stride=2)
        self.layer4 = self._make_layer(
            512,
            3,
            dilation=2,
            multi_grid=(1, 1, 1),
        )
        self.context_encoding = _PSPModule(2048, 512)
        self.edge = _EdgeModule()
        self.decoder = _DecoderModule(num_classes)
        # Preserve upstream's misspelled attribute: checkpoint keys use it.
        self.fushion = nn.Sequential(
            nn.Conv2d(1024, 256, kernel_size=1, bias=False),
            ActivatedBatchNorm2d(256),
            nn.Dropout2d(0.1),
            nn.Conv2d(256, num_classes, kernel_size=1, bias=True),
        )

    def _make_layer(
        self,
        planes: int,
        blocks: int,
        *,
        stride: int = 1,
        dilation: int = 1,
        multi_grid: Sequence[int] | int = 1,
    ) -> nn.Sequential:
        downsample: nn.Module | None = None
        if stride != 1 or self.inplanes != planes * _Bottleneck.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(
                    self.inplanes,
                    planes * _Bottleneck.expansion,
                    kernel_size=1,
                    stride=stride,
                    bias=False,
                ),
                _batch_norm(planes * _Bottleneck.expansion),
            )

        def grid(index: int) -> int:
            if isinstance(multi_grid, Sequence):
                return multi_grid[index % len(multi_grid)]
            return 1

        layers: list[nn.Module] = [
            _Bottleneck(
                self.inplanes,
                planes,
                stride=stride,
                dilation=dilation,
                downsample=downsample,
                multi_grid=grid(0),
            )
        ]
        self.inplanes = planes * _Bottleneck.expansion
        layers.extend(
            _Bottleneck(
                self.inplanes,
                planes,
                dilation=dilation,
                multi_grid=grid(index),
            )
            for index in range(1, blocks)
        )
        return nn.Sequential(*layers)

    def forward(self, tensor: Tensor) -> Tensor:
        input_height, input_width = tensor.shape[2:]
        tensor = self.relu1(self.bn1(self.conv1(tensor)))
        tensor = self.relu2(self.bn2(self.conv2(tensor)))
        tensor = self.relu3(self.bn3(self.conv3(tensor)))
        tensor = self.maxpool(tensor)
        first = self.layer1(tensor)
        second = self.layer2(first)
        third = self.layer3(second)
        fourth = self.layer4(third)
        context = self.context_encoding(fourth)
        _parsing, parsing_features = self.decoder(context, first)
        _edge, edge_features = self.edge(first, second, third)
        fusion = self.fushion(torch.cat([parsing_features, edge_features], dim=1))
        return functional.interpolate(
            fusion,
            size=(input_height, input_width),
            mode="bilinear",
            align_corners=True,
        )
