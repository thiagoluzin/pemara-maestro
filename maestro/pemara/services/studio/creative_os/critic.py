"""CPU temporal diagnostics. These measurements do not establish identity or acting quality."""
import shutil
import subprocess
import numpy as np
from .ir import CreativeError


def temporal_diagnostics(path):
    binary=shutil.which("ffmpeg")
    if not binary: raise CreativeError("FFMPEG_MISSING", "ffmpeg indisponível.",503)
    command=[binary,"-v","error","-threads","1","-i",str(path),"-t","30","-an",
             "-filter_threads","1","-vf","fps=5,scale=160:90:flags=area,format=gray",
             "-f","rawvideo","-pix_fmt","gray","pipe:1"]
    result=subprocess.run(command,capture_output=True,timeout=120,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    if result.returncode or result.stderr or len(result.stdout) % (160*90):
        return {"available":False,"reason":"DECODE_FAILED","error":result.stderr.decode(errors="replace")[:1000]}
    frames=np.frombuffer(result.stdout,dtype=np.uint8).reshape(-1,90,160).astype(np.float32)
    if len(frames)<2: return {"available":False,"reason":"TOO_FEW_FRAMES"}
    motion=np.abs(np.diff(frames,axis=0)).mean(axis=(1,2)) / 255
    laplacian=-4*frames[:,1:-1,1:-1]+frames[:,:-2,1:-1]+frames[:,2:,1:-1]+frames[:,1:-1,:-2]+frames[:,1:-1,2:]
    sharpness=laplacian.var(axis=(1,2))
    sections={}
    for name,indices in zip(("opening","first_third","middle","final_third","ending"),np.array_split(np.arange(len(frames)),5)):
        if not len(indices): continue
        sections[name]={"sample_range":[int(indices[0]),int(indices[-1])],"sharpness_proxy":float(sharpness[indices].mean()),
            "luminance":float(frames[indices].mean()/255)}
    first=sections["opening"]["sharpness_proxy"]
    last=sections.get("ending",sections["opening"])["sharpness_proxy"]
    ratio=(last-first)/max(first,1)
    frozen=float(np.mean(motion < 0.0005))
    flags=[]
    if frozen > .8: flags.append("LOW_MOTION_REVIEW")
    if ratio < -.35: flags.append("SHARPNESS_DROP_REVIEW")
    return {"available":True,"method":"cpu_5fps_160x90_diagnostics","samples":len(frames),
            "sections":sections,"mean_frame_difference":float(motion.mean()),"low_motion_fraction":frozen,
            "sharpness_change_ratio":float(ratio),"review_flags":flags,"semantic_quality_proven":False}
