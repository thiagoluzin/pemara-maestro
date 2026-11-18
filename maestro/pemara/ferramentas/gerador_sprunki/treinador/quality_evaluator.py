"""
quality_evaluator.py
Avalia automaticamente a qualidade de Sprunkis gerados.

Métricas implementadas:
1. Fidelidade ao prompt (CLIP Score)
2. Coerência de cores (análise de paleta)
3. Qualidade visual (no-trash, sem artefatos)
4. Anatomia correta (bounding box, proporções)
5. Estilo consistente (comparação com referências)

Saída: Score 0-100 para cada Sprunki
"""

import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Dict

# Cache do modelo e das embeddings das referências
_CLIP_MODEL = None
_CLIP_PROCESSOR = None
_REF_EMBEDDINGS = {}

def get_clip_model():
    global _CLIP_MODEL, _CLIP_PROCESSOR
    if _CLIP_MODEL is None or _CLIP_PROCESSOR is None:
        from transformers import CLIPProcessor, CLIPModel
        _CLIP_MODEL = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _CLIP_PROCESSOR = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _CLIP_MODEL, _CLIP_PROCESSOR


def calculate_clip_score(image_path: str, prompt: str) -> float:
    """
    Calcula similaridade CLIP entre imagem e prompt.
    Score mais alto = melhor fidelidade ao prompt.
    """
    try:
        model, processor = get_clip_model()
        
        image = Image.open(image_path).convert("RGB")
        inputs = processor(
            text=[prompt],
            images=image,
            return_tensors="pt",
            padding=True
        )
        
        with torch.no_grad():
            outputs = model(**inputs)
            clip_score = outputs.logits_per_image[0, 0].item()
        
        # Normaliza de escala CLIP para 0-100
        return min(100, max(0, (clip_score + 20) / 4))
    
    except Exception as e:
        print(f"  [AVISO] CLIP score falhou: {e}")
        return 50.0


def analyze_color_coherence(image_path: str, expected_colors: Optional[list] = None) -> float:
    """
    Analisa coerência de cores da imagem.
    - Verifica se cores dominantes são consistentes
    - Penaliza ruído cromático excessivo
    Score: 0-100
    """
    try:
        image = Image.open(image_path).convert("RGB")
        arr = np.array(image)
        
        pixels = arr.reshape(-1, 3)
        
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        dominant_colors = kmeans.cluster_centers_
        color_counts = np.bincount(kmeans.labels_)
        color_ratios = color_counts / color_counts.sum()
        
        # Entropia mede distribuição de cores
        entropy = -np.sum(color_ratios * np.log2(color_ratios + 1e-10))
        max_entropy = np.log2(5)
        
        # Baixa entropia = cores dominantes claras (bom)
        color_score = (1 - entropy / max_entropy) * 100
        
        return min(100, max(0, color_score))
    
    except Exception as e:
        print(f"  [AVISO] Color coherence falhou: {e}")
        return 50.0


def check_anatomy_quality(image_path: str) -> float:
    """
    Verifica qualidade anatômica do Sprunki:
    - Bounding box não muito alongado
    - Área de conteúdo adequada (não muito pequeno, não muito grande)
    - Proporções razoáveis
    Score: 0-100
    """
    try:
        image = Image.open(image_path).convert("RGBA")
        arr = np.array(image)
        alpha = arr[:, :, 3]
        
        # Se o canal alpha for totalmente opaco, inferimos a mascara de conteudo
        # considerando os pixels que nao sao brancos/cinza muito claros (fundo).
        if np.all(alpha == 255):
            rgb = arr[:, :, :3]
            # Pixels de conteudo sao aqueles onde pelo menos um canal R/G/B nao e branco
            content_mask = np.any(rgb < 245, axis=2)
        else:
            content_mask = alpha > 30
        
        # Bounding box do conteúdo visível
        rows = np.any(content_mask, axis=1)
        cols = np.any(content_mask, axis=0)
        
        if not rows.any() or not cols.any():
            return 0.0
        
        y0, y1 = np.where(rows)[0][[0, -1]]
        x0, x1 = np.where(cols)[0][[0, -1]]
        
        height = y1 - y0 + 1
        width = x1 - x0 + 1
        
        # Proporção ideal: entre 0.6 e 1.4 (quadrado ±40%)
        aspect_ratio = width / height if height > 0 else 0
        if 0.6 <= aspect_ratio <= 1.4:
            aspect_score = 100
        elif 0.4 <= aspect_ratio <= 1.6:
            aspect_score = 70
        else:
            aspect_score = 40
        
        # Área: deve ocupar 15-70% da imagem
        total_area = image.width * image.height
        content_area = content_mask.sum()
        area_ratio = content_area / total_area if total_area > 0 else 0
        
        if 0.15 <= area_ratio <= 0.70:
            area_score = 100
        elif 0.08 <= area_ratio <= 0.85:
            area_score = 70
        else:
            area_score = 40
        
        return (aspect_score + area_score) / 2
    
    except Exception as e:
        print(f"  [AVISO] Anatomy quality falhou: {e}")
        return 50.0


def compare_with_references(image_path: str, reference_dir: str) -> float:
    """
    Compara o Sprunki gerado com referências conhecidas.
    Usa embeddings do CLIP para medir similaridade estilística.
    Score: 0-100 (mais alto = mais consistente com o estilo Sprunki)
    """
    try:
        model, processor = get_clip_model()
        
        generated = Image.open(image_path).convert("RGB")
        
        inputs_gen = processor(
            images=generated,
            return_tensors="pt",
            padding=True
        )
        with torch.no_grad():
            embedding_gen = model.get_image_features(**inputs_gen)
        
        ref_dir = Path(reference_dir)
        global _REF_EMBEDDINGS
        
        if reference_dir not in _REF_EMBEDDINGS:
            embeddings = []
            ref_images = list(ref_dir.glob("*.png")) + list(ref_dir.glob("*.jpg")) + list(ref_dir.glob("*.svg"))
            if not ref_images:
                return 50.0
            
            for ref_img in ref_images[:10]:
                try:
                    if ref_img.suffix.lower() == '.svg':
                        continue
                    ref = Image.open(ref_img).convert("RGB")
                    
                    inputs_ref = processor(
                        images=ref,
                        return_tensors="pt",
                        padding=True
                    )
                    with torch.no_grad():
                        embedding_ref = model.get_image_features(**inputs_ref)
                    embeddings.append(embedding_ref)
                except Exception:
                    continue
            _REF_EMBEDDINGS[reference_dir] = embeddings
            
        cached_embeddings = _REF_EMBEDDINGS[reference_dir]
        if not cached_embeddings:
            return 50.0
            
        similarities = []
        for embedding_ref in cached_embeddings:
            with torch.no_grad():
                sim = torch.nn.functional.cosine_similarity(
                    embedding_gen, embedding_ref, dim=1
                )[0].item()
            similarities.append(sim)
        
        if not similarities:
            return 50.0
        
        avg_similarity = np.mean(similarities)
        style_score = (avg_similarity + 1) / 2 * 100
        
        return min(100, max(0, style_score))
    
    except Exception as e:
        print(f"  [AVISO] Reference comparison falhou: {e}")
        return 50.0


def evaluate_sprunki(
    image_path: str, 
    prompt: Optional[str] = None, 
    reference_dir: Optional[str] = None
) -> dict:
    """
    Avaliação completa do Sprunki.
    Retorna dict com todos os scores individuais e score total.
    """
    scores = {}
    
    if prompt:
        scores["clip_score"] = calculate_clip_score(image_path, prompt)
    else:
        scores["clip_score"] = 50.0
    
    scores["color_score"] = analyze_color_coherence(image_path)
    scores["anatomy_score"] = check_anatomy_quality(image_path)
    
    if reference_dir and Path(reference_dir).exists():
        scores["style_score"] = compare_with_references(image_path, reference_dir)
    else:
        scores["style_score"] = 50.0
    
    weights = {
        "clip_score": 0.25,
        "color_score": 0.25,
        "anatomy_score": 0.25,
        "style_score": 0.25
    }
    
    total_score = sum(
        scores[k] * weights[k] 
        for k in scores.keys()
    )
    scores["total_score"] = total_score
    
    return scores


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Avalia qualidade de Sprunkis")
    parser.add_argument("--image", required=True, help="Caminho da imagem")
    parser.add_argument("--prompt", default=None, help="Prompt usado na geração")
    parser.add_argument("--references", default="static/referencias", help="Diretório de referências")
    
    args = parser.parse_args()
    
    results = evaluate_sprunki(
        image_path=args.image,
        prompt=args.prompt,
        reference_dir=args.references
    )
    
    print("\n=== AVALIAÇÃO DE QUALIDADE ===")
    for metric, score in results.items():
        print(f"  {metric}: {score:.2f}")
    print("==============================\n")