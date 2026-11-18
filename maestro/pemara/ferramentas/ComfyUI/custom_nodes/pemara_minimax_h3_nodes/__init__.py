"""Pemara-only utility nodes for native MiniMax H3 AV workflows.

This module does not load or call LTX. MiniMax H3 produces a joint NestedTensor
containing video and audio latents; its two native VAEs require those tensors as
separate LATENT inputs.
"""


class MiniMaxH3SeparateAVLatent:
    """Split MiniMax H3's joint AV latent into video and audio latents."""

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"av_latent": ("LATENT",)}}

    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("video_latent", "audio_latent")
    FUNCTION = "separate"
    CATEGORY = "model/latent/minimax"
    DESCRIPTION = "Split a native MiniMax H3 joint AV latent for its video and audio VAEs."

    def separate(self, av_latent):
        samples = av_latent.get("samples")
        if samples is None or not hasattr(samples, "unbind"):
            raise TypeError("MiniMax H3 AV latent must contain an unbindable joint samples value.")

        latents = samples.unbind()
        if len(latents) != 2:
            raise ValueError(
                f"MiniMax H3 AV latent must contain exactly video and audio tensors; got {len(latents)}."
            )

        video_latent = av_latent.copy()
        video_latent["samples"] = latents[0]
        audio_latent = av_latent.copy()
        audio_latent["samples"] = latents[1]

        noise_mask = av_latent.get("noise_mask")
        if noise_mask is not None:
            if not hasattr(noise_mask, "unbind"):
                raise TypeError("MiniMax H3 AV noise_mask must be unbindable when present.")
            masks = noise_mask.unbind()
            if len(masks) != 2:
                raise ValueError(
                    f"MiniMax H3 AV noise_mask must contain exactly two tensors; got {len(masks)}."
                )
            video_latent["noise_mask"] = masks[0]
            audio_latent["noise_mask"] = masks[1]

        return (video_latent, audio_latent)


NODE_CLASS_MAPPINGS = {
    "MiniMaxH3SeparateAVLatent": MiniMaxH3SeparateAVLatent,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MiniMaxH3SeparateAVLatent": "MiniMax H3 Separate AV Latent",
}

from .reference_roles import NODE_CLASS_MAPPINGS as _role_nodes, NODE_DISPLAY_NAME_MAPPINGS as _role_names
NODE_CLASS_MAPPINGS.update(_role_nodes)
NODE_DISPLAY_NAME_MAPPINGS.update(_role_names)
