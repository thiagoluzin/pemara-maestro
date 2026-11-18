"""Narrow native R2V metadata routing, staged only. No torch or service imports."""


def reference_payload(payload, conditioning, expected_images):
    """Replace image references atomically; caller rebuilds native local lists/layout.

    This P14 route allows image-only references. AudioSync's locked source track,
    keyframes, seed and audio scale are preserved outside this reference list.
    Refuse audio/video-reference mixtures because their text tags would differ.
    """
    if len(conditioning) != 1:
        raise RuntimeError('Exactly one positive conditioning entry required')
    metadata = conditioning[0][1]
    refs = metadata.get('minimax_refs')
    if refs is None or len(refs) != expected_images:
        raise RuntimeError('Missing or unexpected number of state-reference images')
    if metadata.get('minimax_token_tags') is None:
        raise RuntimeError('State references require their native matching text token tags')
    for ref in refs:
        if ref.get('kind') != 'image' or ref.get('latent') is None:
            raise RuntimeError('State-reference route requires native encoded image references')
    if any(ref.get('kind') != 'image' for ref in payload.get('refs', [])):
        raise RuntimeError('Global audio/video reference mixture is outside this reviewed image-only route')
    out = dict(payload)
    out['refs'] = list(refs)
    out['text_token_tags'] = metadata['minimax_token_tags']
    # The vendor _window_payload reconstructs these from retained guides and
    # replaced refs in native order; never leave the global bouquet latent cached.
    out.pop('layout',None)
    out.pop('cond_video_latents',None)
    out.pop('cond_audio_latents',None)
    return out
