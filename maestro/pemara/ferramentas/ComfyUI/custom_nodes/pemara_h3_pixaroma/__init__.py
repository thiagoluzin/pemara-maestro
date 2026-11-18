from .bridge import PemaraPixaromaSpectrumLongVideo
from .vendor.node_h3_audio_sync import PixaromaH3AudioSync
from .stage_lock import PemaraH3StageLockedLatent

NODE_CLASS_MAPPINGS = {
    'PemaraPixaromaSpectrumLongVideo': PemaraPixaromaSpectrumLongVideo,
    'PixaromaH3AudioSync': PixaromaH3AudioSync,
    'PemaraH3StageLockedLatent': PemaraH3StageLockedLatent,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'PemaraPixaromaSpectrumLongVideo': 'Pixaroma Long Video + Spectrum (PEMARA pilot)',
    'PixaromaH3AudioSync': 'H3 Audio Sync Pixaroma (Audio Sync 1.4.247)',
    'PemaraH3StageLockedLatent': 'H3 fixed stage / free actor (native inpaint)',
}
