from functools import partial

import torch
import torch.nn as nn
from timm.models.layers import DropPath, to_2tuple

device = "cuda" if torch.cuda.is_available() else "cpu"


# RMS Norm
class RMSNorm(nn.Module):
    def __init__(self, hidden_size, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.variance_epsilon = eps

    def forward(self, hidden_states):
        input_dtype = hidden_states.dtype
        hidden_states = hidden_states.to(torch.float32)
        variance = hidden_states.pow(2).mean(-1, keepdim=True)
        hidden_states = hidden_states * torch.rsqrt(variance + self.variance_epsilon)
        return self.weight * hidden_states.to(input_dtype)


# Layer Scale
class LayerScale(nn.Module):
    def __init__(self, dim, init_values=1e-5, inplace=False, force_fp32=False):
        super().__init__()
        self.inplace = inplace
        self.gamma = nn.Parameter(init_values * torch.ones(dim))
        self.force_fp32 = force_fp32

    @torch.amp.autocast(device, enabled=False)
    def forward(self, x):
        if self.force_fp32:
            output_type = x.dtype
            out = (
                x.float().mul_(self.gamma.float())
                if self.inplace
                else x.float() * self.gamma.float()
            )
            return out.to(dtype=output_type)
        else:
            out = x.mul_(self.gamma) if self.inplace else x * self.gamma
            return out


# FeedForward Layer
class Mlp(nn.Module):
    """MLP as used in Vision Transformer, MLP-Mixer and related networks"""

    def __init__(
        self,
        in_features,
        hidden_features=None,
        out_features=None,
        act_layer=nn.GELU,
        bias=True,
        drop=0.0,
    ):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        bias = to_2tuple(bias)
        drop_probs = to_2tuple(drop)

        self.fc1 = nn.Linear(in_features, hidden_features, bias=bias[0])
        self.act = act_layer()
        self.drop1 = nn.Dropout(drop_probs[0])
        self.fc2 = nn.Linear(hidden_features, out_features, bias=bias[1])
        self.drop2 = nn.Dropout(drop_probs[1])

    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        x = self.drop1(x)
        x = self.fc2(x)
        x = self.drop2(x)
        return x


# Image to Patch
class PatchEmbed(nn.Module):
    """2D Image to Patch Embedding"""

    def __init__(
        self,
        img_size=224,
        patch_size=16,
        in_chans=3,
        embed_dim=768,
        norm_layer=None,
        flatten=True,
    ):
        super().__init__()
        img_size = to_2tuple(img_size)
        patch_size = to_2tuple(patch_size)
        num_patches = (img_size[1] // patch_size[1]) * (img_size[0] // patch_size[0])
        self.patch_shape = (img_size[0] // patch_size[0], img_size[1] // patch_size[1])
        self.img_size = img_size
        self.patch_size = patch_size
        self.num_patches = num_patches
        self.flatten = flatten

        self.proj = nn.Conv2d(
            in_chans, embed_dim, kernel_size=patch_size, stride=patch_size
        )
        self.norm = norm_layer(embed_dim) if norm_layer else nn.Identity()

    def forward(self, x: torch.Tensor, **kwargs):
        x = self.proj(x)
        _, _, H, W = x.shape
        if self.flatten:
            x = x.flatten(2).transpose(1, 2)  # BCHW -> BNC
        x = self.norm(x)
        return x, H, W


# Cross Attention Block
class CrossAttention(nn.Module):
    def __init__(
        self,
        dim,
        num_heads=8,
        qkv_bias=False,
        qk_scale=None,
        attn_drop=0.0,
        proj_drop=0.0,
        attn_head_dim=None,
        out_dim=None,
    ):
        super().__init__()
        if out_dim is None:
            out_dim = dim
        self.num_heads = num_heads
        head_dim = dim // num_heads
        if attn_head_dim is not None:
            head_dim = attn_head_dim
        all_head_dim = head_dim * self.num_heads
        self.scale = qk_scale or head_dim**-0.5
        assert all_head_dim == dim

        self.q = nn.Linear(dim, all_head_dim, bias=False)
        self.k = nn.Linear(dim, all_head_dim, bias=False)
        self.v = nn.Linear(dim, all_head_dim, bias=False)

        if qkv_bias:
            self.q_bias = nn.Parameter(torch.zeros(all_head_dim))
            self.k_bias = nn.Parameter(torch.zeros(all_head_dim))
            self.v_bias = nn.Parameter(torch.zeros(all_head_dim))
        else:
            self.q_bias = None
            self.k_bias = None
            self.v_bias = None

        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(all_head_dim, out_dim)
        self.proj_drop = nn.Dropout(proj_drop)

    def forward(self, x, k=None, v=None):
        B, N, _ = x.shape  # B,N,C
        N_k = k.shape[1]
        N_v = v.shape[1]

        q_bias, k_bias, v_bias = None, None, None
        if self.q_bias is not None:
            q_bias = self.q_bias
            k_bias = self.k_bias
            v_bias = self.v_bias

        q = torch.nn.functional.linear(input=x, weight=self.q.weight, bias=q_bias)
        q = (
            q.reshape(B, N, 1, self.num_heads, -1).permute(2, 0, 3, 1, 4).squeeze(0)
        )  # (B, N_head, N_q, dim)

        k = torch.nn.functional.linear(input=k, weight=self.k.weight, bias=k_bias)
        k = k.reshape(B, N_k, 1, self.num_heads, -1).permute(2, 0, 3, 1, 4).squeeze(0)

        v = torch.nn.functional.linear(input=v, weight=self.v.weight, bias=v_bias)
        v = v.reshape(B, N_v, 1, self.num_heads, -1).permute(2, 0, 3, 1, 4).squeeze(0)

        q = q * self.scale
        attn = q @ k.transpose(-2, -1)  # (B, N_head, N_q, N_k)

        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        x = (attn @ v).transpose(1, 2).reshape(B, N, -1)
        x = self.proj(x)
        x = self.proj_drop(x)

        return x


# Attention Block
class Attention(nn.Module):
    def __init__(
        self,
        dim,
        num_heads=8,
        qkv_bias=False,
        attn_drop=0.0,
        proj_drop=0.0,
        norm_layer=nn.LayerNorm,
        qk_normalization=False,
    ):
        super().__init__()
        assert dim % num_heads == 0, "dim should be divisible by num_heads"
        self.num_heads = num_heads
        head_dim = dim // num_heads
        self.scale = head_dim**-0.5

        self.qkv = nn.Linear(dim, dim * 3, bias=qkv_bias)
        self.attn_drop = nn.Dropout(attn_drop)
        self.proj = nn.Linear(dim, dim)
        self.proj_drop = nn.Dropout(proj_drop)

        self.qk_normalization = qk_normalization
        self.q_norm = norm_layer(dim) if qk_normalization else nn.Identity()
        self.k_norm = norm_layer(dim) if qk_normalization else nn.Identity()

    def _naive_attn(self, x: torch.Tensor):
        B, N, C = x.shape
        qkv = (
            self.qkv(x)
            .reshape(B, N, 3, self.num_heads, C // self.num_heads)
            .permute(2, 0, 3, 1, 4)
        )
        q, k, v = qkv.unbind(0)  # make torchscript happy (cannot use tensor as tuple)

        if self.qk_normalization:
            B_, H_, N_, D_ = q.shape
            q = (
                self.q_norm(q.transpose(1, 2).flatten(-2, -1))
                .view(B_, N_, H_, D_)
                .transpose(1, 2)
            )
            k = (
                self.k_norm(k.transpose(1, 2).flatten(-2, -1))
                .view(B_, N_, H_, D_)
                .transpose(1, 2)
            )

        attn = (q * self.scale) @ k.transpose(-2, -1)
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)

        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        x = self.proj_drop(x)
        return x

    def forward(self, x):
        x = self._naive_attn(x)
        return x


# Single Transformer Block
class Block(nn.Module):
    def __init__(
        self,
        dim,
        num_heads,
        mlp_ratio=4.0,
        qkv_bias=False,
        drop=0.0,
        attn_drop=0.0,
        init_values=None,
        drop_path=0.0,
        act_layer=nn.GELU,
        norm_layer=nn.LayerNorm,
        qk_normalization=False,
        layerscale_force_fp32=False,
    ):
        super().__init__()

        self.norm1 = norm_layer(dim)
        self.attn = Attention(
            dim,
            num_heads=num_heads,
            qkv_bias=qkv_bias,
            attn_drop=attn_drop,
            proj_drop=drop,
            norm_layer=norm_layer,
            qk_normalization=qk_normalization,
        )
        self.ls1 = (
            LayerScale(dim, init_values=init_values, force_fp32=layerscale_force_fp32)
            if init_values
            else nn.Identity()
        )
        # NOTE: drop path for stochastic depth, we shall see if this is better than dropout here
        self.drop_path1 = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()

        self.norm2 = norm_layer(dim)
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = Mlp(
            in_features=dim,
            hidden_features=mlp_hidden_dim,
            act_layer=act_layer,
            drop=drop,
        )
        self.ls2 = (
            LayerScale(dim, init_values=init_values, force_fp32=layerscale_force_fp32)
            if init_values
            else nn.Identity()
        )
        self.drop_path2 = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor):
        x = x + self.drop_path1(self.ls1(self.attn(self.norm1(x))))
        x = x + self.drop_path2(self.ls2(self.mlp(self.norm2(x))))
        return x


class AttentiveBlock(nn.Module):
    def __init__(
        self,
        dim,
        num_heads,
        qkv_bias=False,
        qk_scale=None,
        drop=0.0,
        attn_drop=0.0,
        drop_path=0.0,
        norm_layer=nn.LayerNorm,
        attn_head_dim=None,
        out_dim=None,
    ):
        super().__init__()

        self.norm1_q = norm_layer(dim)
        self.norm1_k = norm_layer(dim)
        self.norm1_v = norm_layer(dim)
        self.cross_attn = CrossAttention(
            dim,
            num_heads=num_heads,
            qkv_bias=qkv_bias,
            qk_scale=qk_scale,
            attn_drop=attn_drop,
            proj_drop=drop,
            attn_head_dim=attn_head_dim,
            out_dim=out_dim,
        )

        self.drop_path = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()

    def forward(self, x_q, x_kv, pos_q, pos_k, bool_masked_pos, rel_pos_bias=None):
        x_q = self.norm1_q(x_q + pos_q)
        x_k = self.norm1_k(x_kv + pos_k)
        x_v = self.norm1_v(x_kv)
        x = self.cross_attn(x_q, k=x_k, v=x_v)
        return x


class AttentionPoolingBlock(AttentiveBlock):
    def forward(self, x):
        x_q = x.mean(1, keepdim=True)
        x_kv, pos_q, pos_k = x, 0, 0
        x = super().forward(
            x_q, x_kv, pos_q, pos_k, bool_masked_pos=None, rel_pos_bias=None
        )
        x = x.squeeze(1)
        return x


class InternViT(nn.Module):
    def __init__(
        self,
        in_chans=3,
        patch_size=14,
        img_size=224,
        qkv_bias=False,  # True
        drop_path_rate=0.0,
        embed_dim=32,
        num_heads=16,
        mlp_ratio=4,
        init_values=0.1,
        qk_normalization=True,
        depth=2,
        layerscale_force_fp32=False,
        cls_target="cls_patch_concat",  # attention_pooling
        num_classes=10,
        norm_type="rms",
    ):
        super().__init__()
        self.num_features = self.embed_dim = (
            embed_dim  # num_features for consistency with other models
        )

        self.drop_path_rate = drop_path_rate
        self.img_size = img_size
        self.patch_size = patch_size
        self.cls_target = cls_target
        self.depth = depth

        if norm_type == "rms":
            norm_layer_for_blocks = partial(RMSNorm, eps=1e-6)
        elif norm_type == "ln":
            norm_layer_for_blocks = partial(nn.LayerNorm, eps=1e-6)
        else:
            raise NotImplementedError

        self.norm_layer_for_blocks = norm_layer_for_blocks
        self.patch_embed = PatchEmbed(img_size, patch_size, in_chans, embed_dim)
        num_patches = self.patch_embed.num_patches
        self.num_patches = num_patches
        self.pos_embed = nn.Parameter(torch.zeros(1, num_patches + 1, embed_dim))
        self.pos_drop = nn.Identity()
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embed_dim))

        dpr = [x.item() for x in torch.linspace(0, drop_path_rate, depth)]

        self.blocks = nn.ModuleList(
            [
                Block(
                    embed_dim,
                    num_heads,
                    mlp_ratio,
                    qkv_bias=qkv_bias,
                    norm_layer=norm_layer_for_blocks,
                    drop_path=dpr[i],
                    init_values=init_values,
                    attn_drop=0.0,
                    qk_normalization=qk_normalization,
                    layerscale_force_fp32=layerscale_force_fp32,
                )
                for i in range(depth)
            ]
        )

        if cls_target == "cls_patch_concat":
            # TODO: changes from original paper:: from nn.SyncBatchNorm to nn.LayerNorm
            self.norm = nn.LayerNorm(embed_dim * 2, eps=1e-6)
            self.head = (
                nn.Linear(embed_dim * 2, num_classes)
                if num_classes > 0
                else nn.Identity()
            )
        elif cls_target == "attention_pooling":
            self.attn_pooling = AttentionPoolingBlock(
                dim=embed_dim,
                num_heads=num_heads,
                qkv_bias=True,
                qk_scale=None,
                drop=0.0,
                attn_drop=0.0,
                norm_layer=partial(nn.LayerNorm, eps=1e-5),
                out_dim=embed_dim,
            )
            # TODO: changes from original paper:: from nn.SyncBatchNorm to nn.LayerNorm
            self.norm = nn.LayerNorm(embed_dim, eps=1e-6)
            self.head = (
                nn.Linear(embed_dim, num_classes) if num_classes > 0 else nn.Identity()
            )

        else:
            raise NotImplementedError

        if type(self.head) != nn.Identity:
            self.head.weight.data.normal_(mean=0.0, std=0.01)
            self.head.bias.data.zero_()

    @property
    def dtype(self):
        return self.patch_embed.proj.weight.dtype

    def forward_features(self, x):
        x, _, _ = self.patch_embed(x.type(self.dtype))
        batch_size, _, _ = x.size()
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x = torch.cat((cls_tokens, x), dim=1)
        x = x + self.pos_embed

        for idx, blk in enumerate(self.blocks):
            x = blk(x)
        return x

    def forward(self, x):
        x = self.forward_features(x)
        if self.cls_target == "cls_patch_concat":
            x = torch.cat((x[:, 0, :], x[:, 1:, :].mean(dim=1)), dim=-1)
        elif self.cls_target == "attention_pooling":
            x = self.attn_pooling(x)
        else:
            raise NotImplementedError

        x = self.norm(x)
        x = self.head(x)
        return x
