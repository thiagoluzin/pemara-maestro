import sys
try:
    import torchvision.transforms.functional as _tvf
    from types import ModuleType as _MT
    _m = _MT("torchvision.transforms.functional_tensor")
    # Copia tudo que basicsr pode pedir
    for _attr in dir(_tvf):
        try: setattr(_m, _attr, getattr(_tvf, _attr))
        except: pass
    sys.modules["torchvision.transforms.functional_tensor"] = _m
    print("[PATCH] torchvision.transforms.functional_tensor injetado OK")
except Exception as e:
    print(f"[PATCH] aviso: {e}")
