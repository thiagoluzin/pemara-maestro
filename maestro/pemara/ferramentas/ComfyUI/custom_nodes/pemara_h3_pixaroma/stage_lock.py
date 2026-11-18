"""Native H3 inpainting for a fixed stage; no restoration or video upscaling."""
import json
import torch
import torch.nn.functional as F
from .vendor._h3_long_video_helpers import frames_of

def prepare_region(region, video):
    if region.ndim != 4 or region.shape[0] != 1:
        raise ValueError('Stage region must be one RGB mask image')
    mask=region[:1,...,0].float().clamp(0,1).unsqueeze(1)
    mask=F.interpolate(mask,size=video.shape[-2:],mode='bilinear',align_corners=False)
    if not (bool((mask==0).any()) and bool((mask==1).any())):
        raise ValueError('Stage lock requires both fixed background and fully free actor regions')
    return mask.unsqueeze(2).expand_as(video).to(video)

class PemaraH3StageLockedLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'latent':('LATENT',),'video_vae':('VAE',),'stage_image':('IMAGE',),'actor_region':('IMAGE',)}}
    RETURN_TYPES=('LATENT',)
    FUNCTION='prepare'
    CATEGORY='PEMARA/H3/Experimental'
    def prepare(self,latent,video_vae,stage_image,actor_region):
        import comfy.nested_tensor
        samples=latent.get('samples')
        if not getattr(samples,'is_nested',False):
            raise ValueError('Expected native H3 video/audio latent')
        video,audio=samples.unbind()
        if video.ndim!=5 or video.shape[0]!=1 or video.shape[1]!=24:
            raise ValueError('Expected one H3 video with24 channels')
        height,width=video.shape[-2]*16,video.shape[-1]*16
        if tuple(stage_image.shape)!=(1,height,width,3):
            raise ValueError('Approved stage must match target dimensions exactly; no resize fallback')
        if tuple(actor_region.shape)!=tuple(stage_image.shape):
            raise ValueError('Actor region geometry differs from approved stage')
        frames=frames_of(video.shape[2])
        pixels=stage_image.expand(frames,-1,-1,-1)
        encoded=video_vae.encode_tiled(pixels,tile_x=512,tile_y=512,overlap=64,tile_t=64,overlap_t=8)
        del pixels
        if tuple(encoded.shape)!=tuple(video.shape):
            raise ValueError(f'Native stage encoding geometry mismatch: {encoded.shape} vs {video.shape}')
        encoded=encoded.to(video)
        region=prepare_region(actor_region,encoded)
        result=dict(latent)
        result['samples']=comfy.nested_tensor.NestedTensor((encoded,audio))
        result['noise_mask']=comfy.nested_tensor.NestedTensor((region,torch.zeros_like(audio)))
        print('[PEMARA H3 stage lock] '+json.dumps({'frames':frames,'latent_shape':list(encoded.shape),
              'actor_fraction':float((region[0,0,0]>0).float().mean()),
              'fixed_background_fraction':float((region[0,0,0]==0).float().mean()),
              'audio_locked':True,'source':'approved incoming frame','method':'native_masked_sampling',
              'restoration':False,'dlss5_video':False}))
        return (result,)
